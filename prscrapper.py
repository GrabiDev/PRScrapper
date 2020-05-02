from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import argparse, re, sys, logging, os

def get_page(url):
  """
  Attempts to get the content at `url` by making an HTTP GET request.
  If the content-type of response is some kind of HTML/XML, return the
  text content, otherwise return None.
  """
  try:
    with closing(get(url, stream=True)) as resp:
      if is_response_good(resp) and is_content_html(resp):
        return resp.content
      else:
        return None

  except RequestException as e:
    log.critical('Error during requests to {0} : {1}'.format(url, str(e)))
    return None

def is_response_good(resp):
  return resp.status_code == 200

def is_content_html(resp):
  """
  Returns True if the response seems to be HTML, False otherwise.
  """
  content_type = resp.headers['Content-Type'].lower()
  return (content_type is not None 
          and content_type.find('html') > -1)

def _setup_custom_logger():
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    #handler = logging.FileHandler(CONFIG_JSON['log_output'], mode='w')
    #handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel('DEBUG')
    #logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger

if __name__ == '__main__':
  # setting up argument parser
  log = _setup_custom_logger()

  parser = argparse.ArgumentParser(description='Downloads mp3 file with Polish Radio programme.')
  parser.add_argument('url', type=str, help='link to polskieradio.pl website where the programme can be heard online')

  args = parser.parse_args()

  # check if argument present
  if not args.url:
    raise ValueError('Missing url argument.')
  
  # download website
  raw_html = get_page(args.url)

  # initialise BeautifulSoup
  soup = BeautifulSoup(raw_html, 'html.parser')

  # find info elements
  programme_title_tag = soup.find_all('h1', class_='title')[0]
  programme_title = programme_title_tag.string.strip()

  if not programme_title:
    programme_title = 'no_title'
  
  programme_date_tag = soup.select('.source-time')[0].select('.time')[0]
  programme_date = programme_date_tag.string.strip()

  if not programme_date:
    programme_date = 'no_date'

  log.info('Found \"' + programme_title + '\" from ' + programme_date)

  # find audio url
  audio_url = ''

  script_tags = soup.find_all('script')

  index = 0
  while audio_url == '':
    matches = re.findall(r'\/\/static\.prsa\.pl\/.*\.mp3', str(script_tags[index].string))
    if len(matches) == 0:
      index += 1;
    else:
      audio_url = matches[0]

  audio_url = 'https:' + audio_url
  log.info('URL detected: ' + audio_url)

  # download blob
  output_file_name = programme_title + ' - ' + programme_date + '.mp3'

  with open(output_file_name, "wb") as f:
    log.info("Downloading to: %s/%s" % (os.getcwd(), output_file_name))
    response = get(audio_url, stream=True)

    total_length = response.headers.get('content-length')

    if total_length is None: # no content length header
      f.write(response.content)
    else:
      dl = 0
      total_length = int(total_length)
      for data in response.iter_content(chunk_size=4096):
        dl += len(data)
        f.write(data)
        done = int(50 * dl / total_length)
        sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )    
        sys.stdout.flush()
      sys.stdout.write('\r%s\r' % (' ' * 52))
      log.info('Download complete!')