#!/usr/bin/env bash
# literary-craft 安装脚本：先暂存 -> 校验 -> 备份 -> 替换；失败自动回滚，保留原有安装。
#
# 用法：
#   bash install.sh <仓库目录> [skill 目录名，默认 literary-craft]
#   WORKBUDDY_SKILLS=~/.workbuddy/skills bash install.sh <仓库目录> interactive-fiction

set -u

src="${1:-}"
skill="${2:-literary-craft}"
say() { printf '  %s\n' "$1"; }
die() { printf '  ✗ %s\n' "$1" >&2; exit 1; }

[ -n "$src" ] || die "缺少参数：请传入仓库目录"
[ -d "$src/$skill" ] || die "校验失败：$src/$skill 不存在"
[ -f "$src/$skill/SKILL.md" ] || die "校验失败：找不到 $skill/SKILL.md"
grep -q "^name: $skill" "$src/$skill/SKILL.md" \
  || die "校验失败：SKILL.md 的 name 不是 $skill"
grep -q '^version:' "$src/$skill/SKILL.md" \
  || die "校验失败：SKILL.md 缺少 version"
ver=$(sed -n 's/^version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p' \
      "$src/$skill/SKILL.md" | head -1)
[ -n "$ver" ] || die "校验失败：version 解析为空"

root="${WORKBUDDY_SKILLS:-$HOME/.workbuddy/skills}"
target="$root/$skill"
stage=$(mktemp -d 2>/dev/null) || die "无法创建临时目录"
backup=""

restore() {
  if [ -n "$backup" ] && [ -d "$backup" ]; then
    rm -rf "$target"
    mv "$backup" "$target"
    printf '  ↩ 已回滚，原有安装保留在 %s\n' "$target" >&2
  fi
}

cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then restore; fi
  rm -rf "$stage"
  exit "$rc"
}
trap cleanup EXIT INT TERM

say "暂存新版本…"
cp -r "$src/$skill" "$stage/$skill" || die "暂存复制失败"
[ -f "$stage/$skill/SKILL.md" ] || die "暂存校验失败：SKILL.md 缺失"

mkdir -p "$root" || die "无法创建 $root"

if [ -e "$target" ]; then
  say "备份旧版本…"
  backup="$root/.$skill.bak.$$"
  rm -rf "$backup"
  mv "$target" "$backup" || die "备份旧版本失败"
fi

# 测试注入点：用于验证"备份后失败能否回滚"，正常安装不会触发
if [ "${CRAFT_INSTALL_FAULT:-}" = "after_backup" ]; then die "（测试注入）替换前失败"; fi

say "替换…"
mv "$stage/$skill" "$target" || die "替换失败"
[ -f "$target/SKILL.md" ] || die "安装后校验失败"

[ -z "$backup" ] || rm -rf "$backup"
say "✓ 安装完成 v$ver → $target"
