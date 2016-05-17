#!/usr/bin/env python

import sys
import requests
import settings
import re

url = 'https://api.medium.com/v1/users/{0}/posts'.format(settings.MEDIUM_USER_ID)

headers = {"Authorization":"Bearer {0}".format(settings.MEDIUM_TOKEN)}

RE_JEKYLL_TAG = re.compile('\{\%.+?\%\}')

# This uses the Y/M/D structure from my blog so not super flexible
# For example 2016-05-11-identifying-unused-database-tables.md => http://dangoldin.com/2016/05/11/identifying-unused-database-tables/
def generate_canonical_url(fn):
    pieces = fn.split('/')[-1].split('-')
    date_path = '/'.join(pieces[0:3])
    post_path = '-'.join(pieces[3:]).replace('.md', '/')
    return settings.ORIGINAL_BASE_URL + date_path + '/' + post_path

def parse_markdown(fn):
    with open(fn, 'r') as f:
        post_data = f.read()

    data = {
        "contentFormat": "markdown",
        "canonicalUrl": generate_canonical_url(fn),
        "publishStatus": "draft"
    }

    content_start = 0
    for i, l in enumerate(post_data.split("\n")[1:]): # Skip the first line
        if l.startswith('title'):
            data['title'] = l.replace('title: ', '').replace('"', '')
        if l.startswith('tags'):
            tags = l.replace('tags: ', '').replace('[', '').replace(']', '').replace('"', '').split(',')
            data['tags'] = [t.replace(' ', '').replace('#', '') for t in tags]
        if l.startswith('---'): # Main content starts here
            content_start = i + 2 # Take into account the skipped row + the --- row

    content = "\n".join(post_data.split("\n")[content_start:]) # Just get the stuff below the ---
    content = RE_JEKYLL_TAG.sub('', content) # Eliminate the Jekyll tags (will break highlighting)
    data['content'] = content

    return data

def post_to_medium(data):
    print 'Publishing:', data
    r = requests.post(url, data=data, headers=headers)
    if r.status_code >= 300: # All below 200 are good
        print 'Error: ', r.content

        # Quick hack to handle error of type: {"errors":[{"message":"Unexpected fields specified.","code":6007}]}
        # Figured out this was due to invalid tags. In this case we can post and remove the tags
        if '6007' in r.content:
            print 'Trying to post without tags'
            del(data['tags'])
            return post_to_medium(data)
        return False
    return True

# python markdown_to_medium.py ~/Dropbox/dev/web/dangoldin.github.com/_posts/2016-05-11-identifying-unused-database-tables.md
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'You must specify a markdown post to convert'

    post_filename = sys.argv[1]

    data = parse_markdown(post_filename)

    if data and 'content' in data:
        post_to_medium(data)
    else:
        print 'Failed to extract post data from markdown'
