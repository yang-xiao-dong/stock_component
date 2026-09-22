# -*- coding: utf-8 -*-
"""统计尚未发布的 feat 提交，生成 CI 发布计划；本模块不推送或发布。"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from builder.build import PROJECT_ROOT, parse_version
from version import __version__

FEATURE_RE = re.compile(r"^feat(?:\([^\r\n)]+\))?!?:\s*\S")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$")


def git(*args, root=PROJECT_ROOT):
    return subprocess.check_output(
        ["git", *args], cwd=root, encoding="utf-8", errors="strict",
    ).strip()


def next_version(current, released=None):
    """递增已发布版本的末段，也允许手动提高 version.py。"""
    current, current_numbers = parse_version(current)
    if released is None:
        # 当前已有本地 1.0.0 分发包，流水线从下一个版本开始。
        released = current
    released, released_numbers = parse_version(released)
    if current_numbers > released_numbers:
        return current
    parts = list(map(int, released.split(".")))
    parts[-1] += 1
    return parse_version(".".join(map(str, parts)))[0]


def make_plan(root=PROJECT_ROOT, current_version=__version__, released_tags=None):
    root = Path(root)
    policy = json.loads((root / ".release-policy.json").read_text(encoding="utf-8"))
    threshold = policy["feature_threshold"]
    if type(threshold) is not int or threshold < 1:
        raise ValueError("feature_threshold 必须是正整数")
    baseline = policy["baseline_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise ValueError("baseline_commit 必须是完整提交 SHA")
    head = git("rev-parse", "HEAD", root=root)
    reachable_tags = git("tag", "--merged", "HEAD", root=root).splitlines()
    if released_tags is not None:
        reachable_tags = [t for t in reachable_tags if t in released_tags]
    versions = []
    for tag in reachable_tags:
        if TAG_RE.fullmatch(tag):
            _, numeric = parse_version(tag[1:])
            versions.append((numeric, tag))
    previous_tag = max(versions)[1] if versions else None
    base = previous_tag or baseline
    subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"],
                   cwd=root, check=True)
    subjects = git("log", "--no-merges", "--format=%s", f"{base}..HEAD", root=root).splitlines()
    features = [subject for subject in subjects if FEATURE_RE.match(subject)]
    version = next_version(current_version, previous_tag[1:] if previous_tag else None)
    return {
        "should_release": len(features) >= threshold,
        "feature_count": len(features),
        "feature_threshold": threshold,
        "version": version,
        "tag": f"v{version}",
        "previous_tag": previous_tag or "",
        "target_commit": head,
        "features": features,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--released-tags", type=Path, help="已正式发布的标签列表，每行一个")
    parser.add_argument("--github-output", type=Path, help="GitHub Actions 步骤输出文件")
    args = parser.parse_args(argv)
    tags = None
    if args.released_tags is not None:
        tags = set(args.released_tags.read_text(encoding="utf-8-sig").splitlines())
    plan = make_plan(released_tags=tags)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key in ("should_release", "feature_count", "version", "tag", "previous_tag", "target_commit"):
                value = plan[key]
                if isinstance(value, bool):
                    value = str(value).lower()
                output.write(f"{key}={value}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"新功能计数：{plan['feature_count']}/{plan['feature_threshold']}\n\n")
            output.write(f"本次发布：{'是' if plan['should_release'] else '否'}；下一版本：{plan['tag']}\n")


if __name__ == "__main__":
    main()
