#!/usr/bin/env python

import os
import re
from pathlib import Path

import questionary
import semver
from git import Repo

# --- 配置区 ---
VERSION_FILE = Path(__file__).parent.parent / 'pyproject.toml'


# --------------


def get_current_version() -> str:
    if not os.path.exists(VERSION_FILE):
        print(f'⚠️ 警告：未找到 {VERSION_FILE.absolute()}，设置版本号为默认值。')
        return '0.1.0'

    with open(VERSION_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        return match.group(1) if match else '0.1.0'


def update_version(new_version: str) -> None:
    with open(VERSION_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        new_content = re.sub(
            r'(version\s*=\s*["\'])[^"\']+(["\'])',
            rf'\g<1>{new_version}\g<2>',
            content,
            count=1,  # 只替换第一个匹配到的版本号（通常就是项目版本）
        )

    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)


def main():
    try:
        repo = Repo('.')
    except Exception as e:
        print(f'❌ 错误：当前目录不是 Git 仓库: {e}')
        return

    if repo.is_dirty():
        print('⚠️ 警告：存在未提交的更改，请先处理后再发布。')
        if not questionary.confirm('强制继续？', default=False).ask():
            return

    # 1. 获取当前版本并生成版本选项
    current_v_str = get_current_version()
    v = semver.VersionInfo.parse(current_v_str)

    # 预定义版本选项逻辑
    version_choices = [
        questionary.Choice(f'major        {v.bump_major()}', value=str(v.bump_major())),
        questionary.Choice(f'minor        {v.bump_minor()}', value=str(v.bump_minor())),
        questionary.Choice(f'patch        {v.bump_patch()}', value=str(v.bump_patch())),
        questionary.Choice(f'next         {v.bump_patch()}', value=str(v.bump_patch())),
        questionary.Choice(f'conventional {v.bump_patch()}', value=str(v.bump_patch())),
        questionary.Choice(f'pre-current  {v.bump_prerelease()}', value=str(v.bump_prerelease())),
        questionary.Choice(
            f'pre-patch    {v.bump_patch().bump_prerelease()}',
            value=str(v.bump_patch().bump_prerelease()),
        ),
        questionary.Choice(
            f'pre-minor    {v.bump_minor().bump_prerelease()}',
            value=str(v.bump_minor().bump_prerelease()),
        ),
        questionary.Choice(
            f'pre-major    {v.bump_major().bump_prerelease()}',
            value=str(v.bump_major().bump_prerelease()),
        ),
        questionary.Choice(f'as-is        {current_v_str}', value=current_v_str),
        questionary.Choice('custom        ...', value='custom'),
    ]

    new_v_str: str = questionary.select(
        f'Current version {current_v_str} »',
        choices=version_choices,
        default=version_choices[4],  # 默认指向 conventional
    ).ask()

    if new_v_str == 'custom':
        new_v_str = questionary.text('Enter version (e.g., 1.2.3):').ask()

    if not new_v_str:
        return

    # 2. Remote 仓库选择（多选）
    remote_names = [r.name for r in repo.remotes]
    if not remote_names:
        print('⚠️ 未发现远程仓库，仅进行本地提交。')
        selected_remotes = []
    else:
        # 构造多选菜单
        remote_choices = [
            questionary.Choice(name, value=name, checked=True) for name in remote_names
        ]

        selected = questionary.checkbox(
            'Remote repo(多选) »',
            choices=remote_choices,
        ).ask()

        selected_remotes = selected

    # 3. 确认执行
    if not questionary.confirm(
        f'确认发布 v{new_v_str} 到 {", ".join(selected_remotes) if selected_remotes else "本地"}?'
    ).ask():
        return

    # 4. 执行更新与提交
    try:
        tag_name = f'v{new_v_str}'
        # 检查本地是否已存在同名 Tag
        if tag_name in repo.tags:
            # 弹出二次确认
            overwrite = questionary.confirm(
                f"本地已存在 Tag '{tag_name}'，是否覆盖（删除并重新创建）?", default=False
            ).ask()

            if overwrite:
                # 解决类型警告：从 repo.tags 字典中获取真正的 TagReference 对象
                repo.delete_tag(repo.tags[tag_name])
                print(f'🗑️ 已删除旧的本地 Tag: {tag_name}')
            else:
                print('🛑 用户取消操作，未创建新 Tag。')
                return  # 或者根据你的逻辑选择 raise 异常
        # 更新 version
        update_version(new_v_str)
        VERSION_FILE.exists() and repo.git.add(VERSION_FILE)
        repo.index.commit(f'chore: release v{new_v_str}')
        # 创建新 Tag
        repo.create_tag(tag_name, message=f'Release version {new_v_str}')
        print(f'🔖 已创建新 Tag: {tag_name}')

        # 5. 推送
        for r_name in selected_remotes:
            remote = repo.remote(r_name)
            print(f'🚀 推送到 {r_name}...')
            remote.push([repo.active_branch.name, tag_name])

        print(f'\n🎉 发布成功！版本: {new_v_str}')
    except Exception as e:
        print(f'❌ 失败: {e}')


if __name__ == '__main__':
    main()
