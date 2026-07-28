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
    r = subprocess.run(
        ['git', '-c', 'credential.helper=',
         '-c', 'http.extraHeader=Authorization: Basic ' + basic,
         'push', 'origin', 'master:main'],
        cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=120, env=env)
    print('push rc =', r.returncode)
    print(r.stdout.strip())
    print(r.stderr.strip())
    if r.returncode == 0:
        print('[OK] 已推送，EdgeOne 约 1-2 分钟自动部署。')
    else:
        print('[FAIL] 推送失败，见上。')

if __name__ == '__main__':
    main()
