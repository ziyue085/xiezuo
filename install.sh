#!/usr/bin/env bash
# literary-craft 安装脚本：先暂存 -> 校验 -> 备份 -> 替换；失败自动回滚，保留原有安装。
#
# 用法：
#   bash install.sh <仓库目录>
#   WORKBUDDY_SKILLS=~/.workbuddy/skills bash install.sh <仓库目录>

set -u

src="${1:-}"
say() { printf '  %s\n' "$1"; }
die() { printf '  ✗ %s\n' "$1" >&2; exit 1; }

[ -n "$src" ] || die "缺少参数：请传入仓库目录"
[ -d "$src/literary-craft" ] || die "校验失败：$src/literary-craft 不存在"
[ -f "$src/literary-craft/SKILL.md" ] || die "校验失败：找不到 SKILL.md"
grep -q '^name: literary-craft' "$src/literary-craft/SKILL.md" \
  || die "校验失败：SKILL.md 的 name 不是 literary-craft"
grep -q '^version:' "$src/literary-craft/SKILL.md" \
  || die "校验失败：SKILL.md 缺少 version"
ver=$(sed -n 's/^version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p' \
      "$src/literary-craft/SKILL.md" | head -1)
[ -n "$ver" ] || die "校验失败：version 解析为空"

root="${WORKBUDDY_SKILLS:-$HOME/.workbuddy/skills}"
target="$root/literary-craft"
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
cp -r "$src/literary-craft" "$stage/literary-craft" || die "暂存复制失败"
[ -f "$stage/literary-craft/SKILL.md" ] || die "暂存校验失败：SKILL.md 缺失"
[ -f "$stage/literary-craft/scripts/craft_lint.py" ] || die "暂存校验失败：缺少 craft_lint.py"

mkdir -p "$root" || die "无法创建 $root"

if [ -e "$target" ]; then
  say "备份旧版本…"
  backup="$root/.literary-craft.bak.$$"
  rm -rf "$backup"
  mv "$target" "$backup" || die "备份旧版本失败"
fi

# 测试注入点：用于验证"备份后失败能否回滚"，正常安装不会触发
if [ "${CRAFT_INSTALL_FAULT:-}" = "after_backup" ]; then die "（测试注入）替换前失败"; fi

say "替换…"
mv "$stage/literary-craft" "$target" || die "替换失败"
[ -f "$target/SKILL.md" ] || die "安装后校验失败"

[ -z "$backup" ] || rm -rf "$backup"
say "✓ 安装完成 v$ver → $target"
