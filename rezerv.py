#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import requests
import json


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

    parser_trains.add_argument('-f', dest='from_city', type=int,
                               help='Code city from')
    parser_trains.add_argument('-t', dest='to_city', type=int,
                               help='Code city to')
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

    url = 'http://www.pz.gov.ua/rezervGR/aj_g60.php'
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Ubuntu Chromium/41.0.2272.76 '
                             'Chrome/41.0.2272.76 Safari/537.36'}
    data = {'kstotpr': args.from_city,
            'kstprib': args.to_city,
            'sdate': args.date}
    resp = requests.post(url, headers=headers, data=data)
    for train in resp.json().get('trains', []):
        print ('%s ### %s//%s - %s//%s ### %s'
               '' % (train['train']['0'],
                     train['otpr'],train['from']['0'],
                     train['to']['0'], train['prib'],
                     train['vputi']))
        if 'l' in train:
            print 'ЛЮКС %s' % train['l']
        if 'k' in train:
            print 'КУПЕ %s' % train['k']
        if 'p' in train:
            print 'ПЛАЦ %s' % train['p']
        if 'c' in train:
            print 'СИДЧ %s' % train['c']
        if 'o' in train:
            print 'ОБЩЙ %s' % train['o']


def stations(args):
    url = 'http://www.pz.gov.ua/rezervGR/aj_stations.php'
    headers = {'Accept': 'application/json, text/javascript, */*',
               'X-Requested-With': 'XMLHttpRequest',
               'Accept-Encoding': 'gzip, deflate, sdch',
               'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Ubuntu Chromium/41.0.2272.76 '
                             'Chrome/41.0.2272.76 Safari/537.36'}
    for q in args.query:
        params = {'stan': q.decode('utf-8')}
        resp = requests.get(url, headers=headers, params=params)
        for item in json.loads(resp.text.split('\n')[-1]):
            print '%s : %s' % (item['f_name'], item['nom'])

if __name__ == '__main__':
    args = parse_cli_args()
    globals()[args.func](args)
