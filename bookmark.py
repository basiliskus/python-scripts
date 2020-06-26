import re
import bs4
import json
import requests


class Bookmark:

  def __init__(self, url='', title='', tags=None, categories=''):
    self.url = url
    self.title = title
    self.tags = tags
    self.categories = categories
    self.last_request = LastHttpRequest(False)
    self.history = []
    # self.status = None

  def parse_json(self, data):
    self.url = data['url']
    self.title = data['title']
    self.tags = data['tags']
    self.categories = data['categories']
    if 'lastHttpRequest' in data:
      self.last_request.parse(data['lastHttpRequest'])
    else:
      self.last_request = LastHttpRequest(False)
    self.history = data['history']

  @property
  def md(self):
    return f'* [{self.title}]({self.url})'

  @property
  def json(self):
    return {
      "url": self.url,
      "title": self.title,
      "tags": self.tags,
      "categories": self.categories,
      "lastHttpRequest": self.last_request.json,
      "history": self.history
    }


class BookmarkCollection:

  title_pattern = r'^(#+)\s+(.+)$'
  # link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'
  link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/.+)\)\s*$'

  def __init__(self):
    self.bookmarks = []

  def load_json(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      data = json.load(file)
      self.parse_json(data)

  def load_md(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      lines = file.readlines()
      self.parse_md(lines)

  def parse_json(self, data):
    for url in data:
      bookmark = Bookmark()
      bookmark.parse_json(data[url])
      self.bookmarks.append(bookmark)

  def parse_md(self, lines):
    cats = []
    for line in lines:
      link_match = re.search(self.link_pattern, line)
      if link_match:
        bookmark = Bookmark(link_match[2], link_match[1])
        tags = [ t.replace(' ', '-').lower() for t in cats ]
        bookmark.tags = [ t.replace(' ', '-').lower() for t in cats ]
        bookmark.categories = ' > '.join(cats)
        self.bookmarks.append(bookmark)
        continue
      title_match = re.search(self.title_pattern, line)
      if title_match:
        category = title_match[2]
        level = title_match[1].count('#') - 1
        cats = cats[:level]
        if len(cats) > level:
          cats[level] = category
        else:
          cats.append(category)

  def write_json(self, fpath):
    with open(fpath, 'w', encoding='utf8') as wf:
      json.dump(self.json, wf, indent=2, ensure_ascii=False)

  def write_md(self, fpath):
    with open(fpath, 'w', encoding='utf8') as wf:
      wf.write(f'{self.md}\n')

  @property
  def json(self):
    data = {}
    for b in self.bookmarks:
      data[b.url] = b.json
    return data

  @property
  def md(self):
    lines = []
    cats = []
    # for bk in sorted(self.bookmarks, key=lambda b: b.categories):
    for bk in self.bookmarks:
      titles = bk.categories.split(' > ')
      for i, t in enumerate(titles, start=1):
        if t in cats: continue
        cats.append(t)
        lines.append(f"\n{'#' * i} {t}")
      lines.append(bk.md)
    return '\n'.join(lines)

  def validate(self):
    for b in self.bookmarks:
      try:
        r = requests.get(b.url)
        b.last_request = LastHttpRequest(True, r.status_code)

        # b.status = r.status_code
        # print(f'{b.url}: {b.status}')

        # get redirect url
        if r.url != b.url:
          b.last_request.redirect = r.url
          # logger.info(f"url: {b.url} => {r.url}")

        # get title
        html = bs4.BeautifulSoup(r.text, 'html.parser')
        t = html.title.text.strip()
        if r.status_code == 200 and b.title != t:
          b.last_request.title = t
          # logger.info(f"title: {b.title} => {t}")

      except Exception as e:
        b.last_request = LastHttpRequest(False)

  def get_bookmarks(self, code):
    return [ b for b in self.bookmarks if b.last_request.status == code ]


class LastHttpRequest:
  def __init__(self, connected, status=None, redirect=None, title=None):
    self.connected = connected
    self.status = status
    self.redirect = redirect
    self.title = title

  def parse(self, data):
    self.connected = data['establishedConnection'] if 'establishedConnection' in data else False
    self.status = data['statusCode'] if 'statusCode' in data else None
    self.redirect = data['redirectUrl'] if 'redirectUrl' in data else None
    self.title = data['pageTitle'] if 'pageTitle' in data else ''

  @property
  def json(self):
    data = { "establishedConnection": self.connected }
    if self.status:
      data["statusCode"] = self.status
    if self.redirect:
      data["redirectUrl"] = self.redirect
    if self.title:
      data["pageTitle"] = self.title
    return data
