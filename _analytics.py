# -*- coding: utf-8 -*-
"""
隐私统计 (Umami) 注入助手。
- 留空 UMAMI_URL / UMAMI_ID 则不打点（返回空串）。
- 填入你的 Umami 实例地址与站点 ID 即可全站启用，反向指导选题。
注意：UMAMI 必须自托管或可信实例，且本仓库是公开仓库——
  若不想把实例地址写进公开代码，请用环境变量或部署平台注入，此处仅作占位。
"""
UMAMI_URL = ''   # 例: 'https://umami.your-domain.com'
UMAMI_ID = ''    # 例: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

def snippet():
    if UMAMI_URL and UMAMI_ID:
        return ('  <script defer src="%s/script.js" data-website-id="%s"></script>\n'
                % (UMAMI_URL.rstrip('/'), UMAMI_ID))
    return ''
