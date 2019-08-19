# encoding: utf-8

import datetime
import errno
import os
import shutil
from operator import itemgetter
from os.path import join

import bibtexparser
import markdown
import yaml
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from dateutil import parser as dtparser
from pyquery import PyQuery as pq

from base import Engine

CWD = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(CWD, 'output')

e = Engine()


def customizations(record):
    author_urls = {
        'Ethan Cecchetti': 'https://www.cs.cornell.edu/~ethan/',
        'Ari Juels': 'http://arijuels.com',
        'Elaine Shi': 'http://elaineshi.com',
        'Ittay Eyal': 'https://www.cs.cornell.edu/~ie53/',
        'Iddo Bentov': 'https://www.cs.cornell.edu/~iddo/',
        'Philip Daian': 'https://pdaian.com/',
    }

    record = convert_to_unicode(record)

    if record.get('ENTRYTYPE') is not 'inproceedings':
        record['draft'] = True
        record['eprint'] = record.get('journal')

    authors = record['author']
    count = authors.count('and') - 1

    def boldface(name):
        return '<b><u>' + name + '</u></b>'

    def linkify(names):
        for a, l in list(author_urls.items()):
            names = names.replace(a, '<a href="%s">%s</a>' % (l, a))
        return names

    # if comma separated, keep it as is
    if ',' in authors:
        authors = authors.replace('Zhang, F', boldface('Zhang, F'))
        authors = authors.replace('Zhang, Fan', boldface('Zhang, Fan'))
    else:
        # keep the last 'and'
        authors = authors.replace('Fan Zhang', boldface('Fan Zhang'))
        authors = authors.replace(' and', ',', count)

        # authors = linkify(authors)
    record['author'] = authors

    record['title'] = record['title'].replace('{', '').replace('}', '')

    # crossref media coverage
    with open('content/media.yaml', 'r') as media_yaml:
        media = yaml.full_load(media_yaml)

    from collections import defaultdict
    media_indexed = defaultdict(list)
    for m in media:
        media_key = m['project'].lower()
        media_indexed[media_key].append({
            'venue': m['venue'],
            'url': m['url']
        })

    if 'mediakey' in record:
        record['media'] = media_indexed[record['mediakey'].lower()]

    return record


def index():
    temp = e.env.get_template('index.html')
    output_fn = e.get_root_fn('index.html')

    with open('content/bio.md') as bio_md:
        bio = markdown.markdown(bio_md.read())

    # with open('content/fan.bib') as bfile:
    with open('content/Zhang_0022:Fan.bib') as bfile:
        bibparser = BibTexParser()
        bibparser.customization = customizations
        bib = bibtexparser.load(bfile, parser=bibparser)

    def parse_md_and_strip(md):
        if not md:
            return None
        # parse markdown and rip off the outer <p>
        text = markdown.markdown(md)
        return pq(text)('p').html()

    # generate update panel
    with open('content/updates.yaml', 'r') as updates_yaml:
        try:
            updates = yaml.full_load(updates_yaml)
            for u in updates:
                if not isinstance(u['date'], datetime.date):
                    u['date'] = dtparser.parse(u.get('date')).date()
                u['date_str'] = u['date'].strftime('%b. %Y')

                u['content'] = parse_md_and_strip(u['content'])
        except yaml.YAMLError as exc:
            print(exc)
            raise

    # sort updates by date
    updates = sorted(updates, key=itemgetter('date'), reverse=True)

    # invited talks
    with open('content/talks.md') as talks_md:
        talks = markdown.markdown(talks_md.read())

    # media coverage
    with open('content/media.yaml', 'r') as media_yaml:
        media = yaml.full_load(media_yaml)

    current_time = datetime.date.today()
    upcoming_news = [n for n in updates if n['date'] >= current_time]
    past_news = [n for n in updates if n['date'] < current_time]

    e.render_and_write(temp,
                       dict(publication=bib.entries,
                            upcoming_news=upcoming_news,
                            past_news=past_news,
                            bio=bio,
                            talks=talks,
                            media=media,
                            ),
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
