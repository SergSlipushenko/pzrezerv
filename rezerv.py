#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import collections
import requests
import json
import pprint

VTYPE_SHORT = {'l': '"Л"', 'k': '"К"', 'p': '"П"'}
VTYPE_LONG = {'l': 'ЛЮКС', 'k': 'КУПЕ', 'p': 'ПЛАЦ', 'o': 'ОБЩЙ', 'c': 'СИДЧ'}


class UTFPPrinter(pprint.PrettyPrinter):
    def format(self, item, context, maxlevels, level):
        if isinstance(item, unicode):
            return item.encode('utf8'), True, False
        return pprint.PrettyPrinter.format(self, item, context,
                                           maxlevels, level)

upprint = UTFPPrinter().pprint

def post(*args, **kwargs):
    debug = kwargs.pop('debug')
    if debug:
        print ''
        print 'POST %s' % next(iter(args))
        print 'Request params'
        upprint(kwargs)
    resp = requests.post(*args, **kwargs)
    if debug:
        print 'Response:'
        try:
            upprint(resp.json())
        except ValueError as e:
            print resp.text
        print ''
    return resp

def parse_cli_args(args=None):

    usage_string = './rezerv.py [-h] <ARG> ...'

    parser = argparse.ArgumentParser(
        description='www.pz.gov.ua cli tool',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=usage_string
    )

    subparsers = parser.add_subparsers(help='Available subcommands.')

    parser_trains = subparsers.add_parser('trains', parents=[],
                                          help='Look for trains')
    parser_trains.add_argument('-v', '--verbose',
                               action='count',
                               help='Verbose output level. '
                                    'Allowed levels = v,vv,vvv, vvvv')
    parser_trains.add_argument('-f', '--from', dest='from_city', type=str,
                               help='City from. Allowed code or name')
    parser_trains.add_argument('-t', '--to', dest='to_city', type=str,
                               help='City to. Allowed code or name')
    parser_trains.add_argument('-d', '--debug', action='store_true',
                               help='Debug')
    parser_trains.add_argument('-n', '--train-number', dest='train_number',
                               type=str,
                               help='Train number. Optional filter')
    parser_trains.add_argument('-q', '--query',
                               type=str,
                               help='Query for tickers. '
                                    'Format: '
                                    '<number: int>'
                                    '-<vagon type: l,k,p,c,o>'
                                    '-<query type, lowers, uppers, '
                                    'pairs, coupes>,...')
    parser_trains.add_argument('date', type=str,
                               help='Travel date xx-xx-xxxx')

    parser_trains.set_defaults(func='get_trains')

    parser_stations = subparsers.add_parser('station', parents=[],
                                            help='Look for station codes')
    parser_stations.add_argument('query', type=str, nargs='+',
                                 help='Query for station name')
    parser_stations.set_defaults(func='guess_station_codes')
    return parser.parse_args(args=args)


def get_trains(args):
    try:
        int(args.from_city)
        from_city = args.from_city
    except ValueError:
        possible_codes = _rezolve_code(args.from_city)
        if possible_codes:
            from_city = possible_codes[0]['nom']
            print 'ГОРОД ОТПРАВЛЕНИЯ ', possible_codes[0]['f_name']
        else:
            print 'ГОРОД ОТПРАВЛЕНИЯ НЕ ОПРЕДЕЛЕН'
            exit(1)

    try:
        int(args.to_city)
        to_city = args.to_city
    except ValueError:
        possible_codes = _rezolve_code(args.to_city)
        if possible_codes:
            to_city = possible_codes[0]['nom']
            print 'ГОРОД ПРИБЫТИЯ ', possible_codes[0]['f_name']
        else:
            print 'ГОРОД ПРИБЫТИЯ НЕ ОПРЕДЕЛЕН'
            exit(1)

    url = 'http://www.pz.gov.ua/'
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Ubuntu Chromium/41.0.2272.76 '
                         'Chrome/41.0.2272.76 Safari/537.36'}
    resp = requests.get(url, headers=headers)
    session_id = resp.cookies['PHPSESSID']
    url = 'http://www.pz.gov.ua/rezervGR/aj_g60.php'
    headers = {'Accept': 'application/json, text/javascript, */*',
               'Accept-Encoding': 'gzip, deflate',
               'Accept-Language': 'ru,en-US;q=0.8,en;q=0.6,uk;q=0.4',
               'Cache-Control': 'no-cache',
               'Connection': 'keep-alive',
               'Content-Length': '105',
               'Content-Type': 'application/x-www-form-urlencoded',
               'Cookie': 'PHPSESSID=%s' % session_id,
               'DNT': '1',
               'Host': 'www.pz.gov.ua',
               'Origin': 'http://www.pz.gov.ua',
               'Pragma': 'no-cache',
               'Referer': 'http://www.pz.gov.ua/rezervGR/',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Ubuntu Chromium/41.0.2272.76 '
                             'Chrome/41.0.2272.76 Safari/537.36',
               'X-Requested-With': 'XMLHttpRequest'}
    data = {'kstotpr': from_city,
            'kstprib': to_city,
            'sdate': args.date}
    resp = post(url, headers=headers, data=data, debug=args.debug)
    trains = resp.json().get('trains', [])
    stat = collections.defaultdict(lambda: collections.defaultdict(int))
    if args.train_number:
        trains = [train for train in trains
                  if train['train']['0'] == args.train_number.decode('utf-8')]

    queries = []
    if args.query:
        for query in args.query.split(','):
            number, vtype, qtype = query.split('.')
            queries.extend([(vtype, qtype)]*int(number))

    result = []

    for train in trains:
        stat = collections.defaultdict(lambda: collections.defaultdict(int))
        metric = collections.defaultdict(
            lambda: collections.defaultdict(
                lambda: collections.defaultdict(list)))
        print ('%s ### %s//%s - %s//%s ### %s'
               '' % (train['train']['0'],
                     train['otpr'],train['from']['0'],
                     train['to']['0'], train['prib'],
                     train['vputi']))
        if not args.verbose and not args.query:
            continue
        if args.verbose == 1 and not args.query:
            print ' '.join(('%s %s' % (VTYPE_LONG[vtype], train[vtype])
                            for vtype in ('l', 'k', 'p', 'c', 'o')))
            print
            continue

        for vtype in ('l', 'k', 'p', 'c', 'o'):
            print '%s %s' % (VTYPE_LONG[vtype], train[vtype])
            if (args.verbose >= 2 or args.query) and vtype in ('l', 'k', 'p'):
                data = {'nomtrain': '"%s"' % train['train']['0'],
                        'typevag': VTYPE_SHORT[vtype],
                        'nametrain': '%s-%s' % (train['from']['0'],
                                                train['to']['0']),
                        'timeotpr': train['otpr'],
                        'timeprib': train['prib']}
                url = 'http://www.pz.gov.ua/rezervGR/aj_g81.php'
                resp = post(url, headers=headers, data=data,
                            debug=args.debug).json()
                for vagon in resp.get('vagons', []):
                    n = vagon['number']
                    places = [int(p) for p in vagon['mesta']]
                    metric[n][vtype]['total'] = places
                    if vtype == 'l':
                        metric[n][vtype]['uppers'] = []
                        metric[n][vtype]['lowers'] = places
                        metric[n][vtype]['pairs'] = []
                        metric[n][vtype]['coupes'] = [
                            (p, p + 1) for p in places
                            if p % 2 == 1 and p + 1 in places]
                    else:
                        metric[n][vtype]['uppers'] = [p for p in places
                                                      if p % 2 == 0]
                        metric[n][vtype]['lowers'] = [p for p in places
                                                      if p % 2 == 1]
                        metric[n][vtype]['pairs'] = [
                            (p, p + 1) for p in places
                            if p % 2 == 1 and p + 1 in places]
                        metric[n][vtype]['coupes'] = [
                            (p, p + 1, p + 2, p + 3)
                            for p in metric[vtype]['total']
                            if p <= 33
                            and p % 4 == 1
                            and p + 1 in places
                            and p + 2 in places
                            and p + 3 in places]

                    for metric_type in ('total', 'lowers', 'uppers',
                                        'pairs', 'coupes'):
                        stat[vtype][metric_type] += \
                            len(metric[n][vtype][metric_type])

                        metric_ = metric[n][vtype][metric_type][:]
                        while metric_ and ((vtype, metric_type) in queries):
                            result.append(((vtype, metric_type),
                                           n, metric_.pop(0)))
                            queries.remove((vtype, metric_type))

                    if args.verbose >= 4:
                        print 'ВАГОН: ', n
                        if metric[n][vtype]['uppers']:
                            print 'ВЕРХНИЕ: %s' % metric[n][vtype]['uppers']
                        if metric[n][vtype]['lowers']:
                            print 'НИЖНИЕ: %s' % metric[n][vtype]['lowers']
                        if metric[n][vtype]['pairs']:
                            print 'ВЕРХ+НИЗ: %s' % metric[n][vtype]['pairs']
                        if metric[n][vtype]['coupes']:
                            print 'КУПЕ: %s' % metric[n][vtype]['coupes']
                    elif args.verbose >= 3:
                        print 'ВАГОН: ', vagon['number']
                        print 'МЕСТА: %s' % metric[n][vtype]['total']

                print ('ВСЕГО: %s НИЖНИЕ: %s ВЕРХНИЕ: %s ВЕРХ+НИЗ: %s КУПЕ: %s'
                       '' % (stat[vtype]['total'],
                             stat[vtype]['lowers'],
                             stat[vtype]['uppers'],
                             stat[vtype]['pairs'],
                             stat[vtype]['coupes']))
            for key in stat[vtype]:
                stat[vtype][key] += stat[vtype][key]

    if result:
        print 'НАЙДЕНО:'
        for r in result:
            q, vagon_number, places = r
            print '{}: ВАГОН: {}  МЕСТА: {}' \
                  ''.format('.'.join(q), vagon_number, str(places))
    if queries:
        print 'НЕ НАЙДЕНО:'
        for q in queries:
            print '.'.join(q)
        exit(1)


def _rezolve_code(query):
    url = 'http://www.pz.gov.ua/rezervGR/aj_stations.php'
    headers = {'Accept': 'application/json, text/javascript, */*',
               'X-Requested-With': 'XMLHttpRequest',
               'Accept-Encoding': 'gzip, deflate, sdch',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Ubuntu Chromium/41.0.2272.76 '
                             'Chrome/41.0.2272.76 Safari/537.36'}
    params = {'stan': query}
    resp = requests.get(url, headers=headers, params=params)
    return json.loads(resp.text.split('\n')[-1])


def guess_station_codes(args):
    for q in args.query:
        for item in _rezolve_code(q):
            print '%s : %s' % (item['f_name'], item['nom'])

if __name__ == '__main__':
    args_ = parse_cli_args()
    globals()[args_.func](args_)
