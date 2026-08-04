#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
一键发布脚本（供小虾[AI]自主发布用）。
读取仓库【外部】的 token 文件（C:\Users\Admin\.qclaw\workspace\.github_token），
执行 git push origin master:main，触发 .github/workflows/deploy.yml 自动部署 EdgeOne。
⚠️ token 文件刻意放在仓库目录之外，绝不进入 git 跟踪，避免公开仓库泄露凭据。
"""
import io, os, subprocess, base64, sys

REPO = r'C:\Users\Admin\.qclaw\workspace\taisei-weekly-reports'
TOKEN_FILE = r'C:\Users\Admin\.qclaw\workspace\.github_token'

def main():
    if not os.path.isfile(TOKEN_FILE):
        print('[ERR] token 文件不存在: ' + TOKEN_FILE)
        sys.exit(1)
    tok = io.open(TOKEN_FILE, encoding='utf-8').read().strip()
    if not tok:
        print('[ERR] token 为空'); sys.exit(1)

    basic = base64.b64encode((tok + ':').encode('utf-8')).decode('ascii')
    env = dict(os.environ)
    env['GIT_TERMINAL_PROMPT'] = '0'

    def git(*args, timeout=120):
        r = subprocess.run(
            ['git', '-c', 'credential.helper=',
             '-c', 'http.extraHeader=Authorization: Basic ' + basic] + list(args),
            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout, env=env)
        print('$ git', ' '.join(args), '->', r.returncode)
        if r.stdout.strip():
            print(r.stdout.strip())
        if r.stderr.strip():
            print(r.stderr.strip())
        return r

    # 先拉取远端 main 并并入本地 master，避免周报自动更新抢跑导致 non-fast-forward。
    # 远端只动周报(index.html/weekly_data_sample.json)，与平台文件无冲突；
    # 若万一冲突，fetch 阶段会报错暴露，而非静默覆盖。
    fr = git('fetch', 'origin', 'main')
    if fr.returncode == 0:
        git('merge', '--no-edit', 'origin/main')

    r = git('push', 'origin', 'master:main')
    print('push rc =', r.returncode)
    if r.returncode == 0:
        print('[OK] 已推送，EdgeOne 约 1-2 分钟自动部署。')
    else:
        print('[FAIL] 推送失败，见上。')

if __name__ == '__main__':
    main()
