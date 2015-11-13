#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import requests
import json

VTYPE_SHORT = {'l': '"Л"', 'k': '"К"', 'p': '"П"'}
VTYPE_LONG = {'l': 'ЛЮКС', 'k': 'КУПЕ', 'p': 'ПЛАЦ', 'o': 'ОБЩЙ', 'c': 'СИДЧ'}

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
                               help='Verbose output level. Allowed levels = v,vv,vvv.')
    parser_trains.add_argument('-f', dest='from_city', type=str,
                               help='City from. Allowed code or name')
    parser_trains.add_argument('-t', dest='to_city', type=str,
                               help='City to. Allowed code or name')
    parser_trains.add_argument('-n', dest='train_number', type=str,
                               help='Train number. Optional filter')
    parser_trains.add_argument('date', type=str,
                               help='Travel date')

    parser_trains.set_defaults(func='trains')

    parser_stations = subparsers.add_parser('station', parents=[],
                                            help='Look for station codes')
    parser_stations.add_argument('query', type=str, nargs='+',
                                 help='Query for station name')
    parser_stations.set_defaults(func='stations')
    return parser.parse_args(args=args)


def trains(args):
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
    resp = requests.post(url, headers=headers, data=data)
    if args.train_number:
        trains = [train for train in resp.json().get('trains', [])
                  if train['train']['0'] == args.train_number.decode('utf-8')]
    else:
        trains = resp.json().get('trains', [])
    for train in trains:
        print ('%s ### %s//%s - %s//%s ### %s'
               '' % (train['train']['0'],
                     train['otpr'],train['from']['0'],
                     train['to']['0'], train['prib'],
                     train['vputi']))
        if not args.verbose:
            continue
        if args.verbose == 1:
            print ' '.join(('%s %s' % (VTYPE_LONG[vtype], train[vtype])
                            for vtype in ('l', 'k', 'p', 'c', 'o')))
            print
            continue
        for vtype in ('l', 'k', 'p', 'c', 'o'):
            print '%s %s' % (VTYPE_LONG[vtype], train[vtype])
            if args.verbose >= 2 and vtype in ('l', 'k', 'p'):
                data = {'nomtrain': '"%s"' % train['train']['0'],
                        'typevag': VTYPE_SHORT[vtype],
                        'nametrain': '%s-%s' % (train['from']['0'],
                                                train['to']['0']),
                        'timeotpr': train['otpr'],
                        'timeprib': train['prib']}
                url = 'http://www.pz.gov.ua/rezervGR/aj_g81.php'
                resp = requests.post(url, headers=headers, data=data).json()
                stat = {'total': 0,
                        'lowers': 0,
                        'pairs': 0,
                        'coupes': 0}
                for vagon in resp.get('vagons', []):
                    places = [int(p) for p in vagon['mesta']]
                    if not places:
                        continue
                    uppers = [p for p in places if p % 2 == 0]
                    lowers = [p for p in places if p % 2 == 1]
                    pairs = [(p, p + 1) for p in places
                             if p % 2 == 1
                             and p + 1 in places]
                    coupes = [(p, p + 1, p + 2, p + 3) for p in places
                              if p <= 33
                              and p % 4 == 1
                              and p + 1 in places
                              and p + 2 in places
                              and p + 3 in places]
                    stat['total'] += len(places)
                    stat['lowers'] += len(lowers)
                    stat['pairs'] += len(pairs)
                    stat['coupes'] += len(coupes)
                    if args.verbose >= 4:
                        print 'ВАГОН: ', vagon['number']
                        if uppers:
                            print 'ВЕРХНИЕ: %s' % uppers
                        if lowers:
                            print 'НИЖНИЕ: %s' % lowers
                        if pairs:
                            print 'ВЕРХ+НИЗ: %s' % pairs
                        if coupes:
                            print 'КУПЕ: %s' % coupes
                    elif args.verbose >= 3:
                        print 'ВАГОН: ', vagon['number']
                        print 'МЕСТА: %s' % places

                print ('ВСЕГО: %s НИЖНИЕ: %s ВЕРХ+НИЗ: %s КУПЕ: %s'
                       '' % (stat['total'], stat['lowers'],
                             stat['pairs'], stat['coupes']))

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


def stations(args):
    for q in args.query:
        for item in _rezolve_code(q):
            print '%s : %s' % (item['f_name'], item['nom'])

if __name__ == '__main__':
    args_ = parse_cli_args()
    globals()[args_.func](args_)
