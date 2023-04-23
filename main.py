import sys
from datetime import datetime
from bs4 import BeautifulSoup
from requests import get
import dateparser
from dateutil.tz import tzlocal

USE_TITLE = False

class ParseResult:
    def __init__(self, date: datetime, title: str, text: str) -> None:
        self.date = date
        self.title = title
        self.text = text

def error(errorString: str):
    print('Error: ' + errorString)
    sys.exit(1)

def parse_date(date: str):
    return dateparser.parse(date).astimezone(tzlocal())

def default_parser(soup: BeautifulSoup, _type: str) -> ParseResult:
    # Try to get some basic information
    return ParseResult(
        date=datetime.now(),
        title=soup.find('title').text,
        text=soup.find('title').text
    )

def reddit_parser(soup: BeautifulSoup, _type: str) -> ParseResult:

    if _type == 'Comment':
        # Comment
        post = soup.find('div', class_='comment')

        return ParseResult(
            date=parse_date(post.find('time').attrs.get('datetime')),
            title=soup.find('title').text, 
            text=post.find('div', class_='usertext-body').text
        )
    
    # Regular post
    post = soup.find('div', class_='entry')

    return ParseResult(
        date=parse_date(post.find('time').attrs.get('datetime')),
        title=post.find('a', class_='title').text,
        text=post.find('div', class_='usertext-body').text
    )

def nitter_parser(soup: BeautifulSoup, _type: str):
    post = soup.find('div', class_='main-tweet')

    return ParseResult(
        date=parse_date(post.find('p', class_='tweet-published').text.replace('·', '')),
        title=soup.find('title').text.removesuffix(' | nitter'),
        text=post.find('div', class_='tweet-content media-body').text
    )

def linkedin_parser(soup: BeautifulSoup, _type: str):
    post = soup.find('article')

    return ParseResult(
        date=parse_date(post.find('time').text.strip().split(' ')[0]),
        title=soup.find('title').text,
        text=post.find('p', class_='attributed-text-segment-list__content').text
    )

def parse(url: str, headers: object, timeout: int):
    site = {'parser': default_parser, 'type': 'Article', 'origin': ''}
    request_url = url

    # figure out what site we're on and transform the url if needed
    if 'reddit.com' in url:
        # We use old reddit since it's lighter to load.
        request_url = url.replace('www.reddit.com', 'old.reddit.com')
        site['parser'] = reddit_parser
        site['origin'] = 'Reddit'
        site['type'] = 'Comment' if '/comment/' in url else 'Post'
    
    elif 'twitter.com' in url:
        # The twitter site now forces JS so we use an alternate.
        request_url = url.replace('twitter.com', 'nitter.net')
        site['origin'] = 'Twitter'
        site['parser'] = nitter_parser
        site['type'] = 'Post'

    elif 'linkedin.com' in url:
        # Linkedin doesn't require any extra work!
        site['origin'] = 'Linkedin'
        site['parser'] = linkedin_parser
        site['type'] = 'Post'
    
    response = None

    try:
        response = get(url=request_url, timeout=timeout, headers=headers)
    except:
        error('Failed to send request to address.')

    if not response.ok:
        error('Request failed with code ' + str(response.status_code))
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        parsed = site['parser'](soup, site['type'])

        print(
            parsed.date.strftime("%Y-%m-%d %H:%M:%S") + '\t' + 
            url + '\t' + 
            site['origin'] + '\t' + 
            site['type'] + '\t' + 
            ((parsed.title.replace('\n', ' ') + '\t') if USE_TITLE else '') + 
            parsed.text.replace('\n', ' ')
        )
    except Exception as ex:
        error('Failed to parse the webpage: ' + str(ex))

if len(sys.argv) != 2:
    error('No URL supplied.')

parse(url=sys.argv[1], headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/111.0' # we pretend to be a real browser to make sites happy.
}, timeout=2 * 1000)