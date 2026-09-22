# -*- coding: utf-8 -*-
"""在临时 Git 仓库内验证功能计数和版本边界，不访问网络。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from builder.release import make_plan, next_version


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Release Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.commit('feat: 历史功能不计入新的发布周期')
        self.policy = {'feature_threshold': 5, 'baseline_commit': self.git('rev-parse', 'HEAD')}
        self.write_policy()
        self.git('add', '.release-policy.json')
        self.commit('chore: 配置发布计数起点')

    def git(self, *args):
        return subprocess.check_output(
            ['git', '-c', 'commit.gpgsign=false', *args], cwd=self.root,
            encoding='utf-8', stderr=subprocess.PIPE,
        ).strip()

    def commit(self, title):
        self.git('commit', '--allow-empty', '-m', title)

    def write_policy(self):
        (self.root / '.release-policy.json').write_text(json.dumps(self.policy), encoding='utf-8')

    def plan(self, **kwargs):
        return make_plan(self.root, current_version='1.0.0', **kwargs)

    def test_release_at_five_features_only(self):
        self.assertEqual(self.plan()['feature_count'], 0)
        for index in range(1, 7):
            self.commit(f'feat: 新功能 {index}')
            plan = self.plan()
            self.assertEqual(plan['feature_count'], index)
            self.assertEqual(plan['should_release'], index >= 5)
            self.assertEqual(plan['tag'], 'v1.0.1')
            self.assertEqual(plan['target_commit'], self.git('rev-parse', 'HEAD'))

    def test_fixes_docs_and_release_commits_do_not_count(self):
        for title in ('fix: 修复图表', 'docs: 更新说明', 'chore: 发布版本', '完善 feat: 提示'):
            self.commit(title)
        self.commit('feat(chart): 增加图表')
        self.commit('feat!: 调整组件接口')
        self.assertEqual(self.plan()['feature_count'], 2)

    def test_new_release_resets_count(self):
        for index in range(5):
            self.commit(f'feat: 功能 {index}')
        self.git('tag', 'v1.0.1')
        self.commit('fix: 修复显示')
        self.commit('feat: 下一批功能')
        plan = self.plan(released_tags={'v1.0.1'})
        self.assertFalse(plan['should_release'])
        self.assertEqual(plan['feature_count'], 1)
        self.assertEqual(plan['previous_tag'], 'v1.0.1')
        self.assertEqual(plan['version'], '1.0.2')

    def test_unpublished_tags_do_not_reset_count(self):
        self.commit('feat: 功能一')
        self.git('tag', 'v1.0.1')
        self.commit('feat: 功能二')
        self.git('tag', 'v9.0.0')
        plan = self.plan(released_tags=set())
        self.assertEqual(plan['feature_count'], 2)
        self.assertEqual(plan['tag'], 'v1.0.1')

    def test_unmerged_release_does_not_change_version(self):
        self.git('checkout', '-b', 'other')
        self.commit('feat: 未合入的功能')
        self.git('tag', 'v9.0.0')
        self.git('checkout', 'main')
        self.assertEqual(self.plan()['tag'], 'v1.0.1')

    def test_merge_counts_feature_once(self):
        self.git('checkout', '-b', 'feature')
        self.commit('feat: 分支功能')
        self.git('checkout', 'main')
        self.git('merge', '--no-ff', 'feature', '-m', 'feat: 合并分支功能')
        self.assertEqual(self.plan()['feature_count'], 1)

    def test_invalid_threshold_is_rejected(self):
        for threshold in (0, -1, True, '5'):
            self.policy['feature_threshold'] = threshold
            self.write_policy()
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                self.plan()

    def test_version_increment(self):
        self.assertEqual(next_version('1.0.0'), '1.0.1')
        self.assertEqual(next_version('1.0.0', '1.2.9'), '1.2.10')
        self.assertEqual(next_version('2.0.0', '1.2.9'), '2.0.0')
        self.assertEqual(next_version('1.0.0', '1.2.3.4'), '1.2.3.5')
        with self.assertRaises(ValueError):
            next_version('1.0.0', '1.0.65535')


if __name__ == '__main__':
    unittest.main()
