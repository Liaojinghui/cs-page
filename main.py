# encoding: utf-8

import datetime
import os
from os.path import join
import markdown
import yaml
from dateutil import parser as dtparser
import bibtexparser

from base import Engine

CWD = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(CWD, 'output')

e = Engine()

from bibtexparser.bparser import BibTexParser


def customizations(record):
    author_urls = {
        'Ethan Cecchetti': 'https://www.cs.cornell.edu/~ethan/',
        'Ari Juels': 'http://arijuels.com',
        'Elaine Shi': 'http://elaineshi.com',
        'Ittay Eyal': 'https://www.cs.cornell.edu/~ie53/',
        'Iddo Bentov': 'https://www.cs.cornell.edu/~iddo/',
    }

    authors = record['author']
    count = authors.count('and') - 1

    def boldface(name):
        return '<b><u>' + name + '</u></b>'

    def linkify(names):
        for a, l in author_urls.items():
            names = names.replace(a, '<a href="%s">%s</a>' % (l, a))
        return names

    # if comma separated, keep it as is
    if ',' in authors:
        authors = authors.replace('Zhang, Fan', boldface('Zhang, Fan'))
    else:
        # keep the last 'and'
        authors = authors.replace('Fan Zhang', boldface('Fan Zhang'))
        authors = authors.replace(' and', ',', count)

        authors = linkify(authors)
    record['author'] = authors

    record['title'] = record['title'].replace('{', '').replace('}', '')
    return record


def index():
    temp = e.env.get_template('index.html')
    output_fn = e.get_root_fn('index.html')

    with open('content/fan.bib') as bfile:
        bib = bfile.read()

    with open('content/bio.md') as bio_md:
        bio = markdown.markdown(bio_md.read())

    bibparser = BibTexParser()
    bibparser.customization = customizations
    bib = bibtexparser.loads(bib, parser=bibparser)

    def parse_md_and_strip(md):
        if not md:
            return None
        # parse markdown and rip off the outer <p>
        text = markdown.markdown(md)
        from pyquery import PyQuery as pq
        return pq(text)('p').html()

    # generate update panel
    with open('content/updates.yaml', 'r') as updates_yaml:
        try:
            updates = yaml.load(updates_yaml)
            for u in updates:
                if not isinstance(u['date'], datetime.date):
                    u['date'] = dtparser.parse(u.get('date')).date()
                u['date_str'] = u['date'].strftime('%b %d, %Y')

                u['content'] = parse_md_and_strip(u['content'])
        except yaml.YAMLError as exc:
            print exc
            raise

    # sort updates by date
    from operator import itemgetter
    updates = sorted(updates, key=itemgetter('date'), reverse=True)

    current_time = datetime.date.today()
    upcoming_news = filter(lambda n: n['date'] >= current_time, updates)
    past_news = filter(lambda n: n['date'] < current_time, updates)

    e.render_and_write(temp,
                       dict(publications=bib.entries,
                            upcoming_news=upcoming_news,
                            past_news=past_news,
                            bio=bio),
                       output_fn)


def page_not_found():
    output = e.get_root_fn('404.html')
    temp = e.env.get_template('base.html')

    with open('./content/404.html', 'r') as c:
        content = c.read()

    e.render_and_write(temp, dict(
        title='Woops',
        content=content),
                       output)


import shutil
import errno

if __name__ == '__main__':
    index()
    page_not_found()

    try:
        shutil.copytree('static', join(OUTPUT_DIR, 'static'))
        shutil.copytree('files', join(OUTPUT_DIR, 'files'))
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise
