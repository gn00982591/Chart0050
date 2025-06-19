name: Generate 0050 Charts

# 1. 觸發條件：推送到 main 分支或每天早上台北時間 6:00 自動執行
on:
  push:
    branches:
      - main
  schedule:
    - cron: '22 22 * * *' # UTC 22:00 = TST 06:00

jobs:
  build:
    runs-on: ubuntu-latest
    concurrency:                # 2. 加入 concurrency，避免重複排程
      group: '0050-chart-gen'
      cancel-in-progress: true

    strategy:
      matrix:
        python-version: [3.10]  # 3. 版本矩陣，未來可擴展到 3.11、3.9

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip dependencies   # 4. 快取 pip，加速安裝
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run chart generation     # 5. 分離成獨立腳本，易於維護
        run: python scripts/generate_charts.py

      - name: Upload HTML artifact     # 6. 上傳輸出檔案，方便後續部署或檢視
        uses: actions/upload-artifact@v3
        with:
          name: 0050-feed-chart
          path: 0050_charts.html

      - name: (選用) Deploy to GitHub Pages  # 7. 直接部署到 Pages（若需要）
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
          publish_branch: gh-pages
