from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd


def initialize(context):
    g.stockindex = '000001.XSHG'
    set_benchmark('000001.XSHG')
    set_option('use_real_price', 'True')
    set_option('order_volume_ration', 1)
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001,
                             open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')


g.stocknum = 30
g.Transfer_date = (1, 4, 8, 10)
run_monthly(trade, monthday=20, time='open')


def trade(context):
    months = context.current_dt.month
    if months in g.Transfer_date:
        Buylist = check_stocks(context)
        if len(context.portfolio.positions) > 0:
            for stock in context.portfolio.positions.keys():
                if stock not in Buylist:
                    order_target(stock, 0)
                    if len(context.portfolio.positions) < g.stocknum:
                        Num = g.stocknum - len(context.portfolio.positions)
                        Cash = context.portfolio.cash/Num
                    else:
                        Cash = 0
                    if len(Buylist) > 0:
                        for stock in Buylist:
                            if stock not in context.portfolio.positions.keys():
                                order_value(stock, cash)
    else:
        return


def check_stocks(context):
    security = get_index_stocks(g.stockindex)
    Stocks = get_fundamentals(query(valuation.code, valuation.pb_ratio,
                                    valuation.pe_ratio,
                                    valuation.circulating_market_cap,
                                    balance.total_assets,
                                    balance.total_liability,
                                    balance.total_current_assets,
                                    balance.total_current_liability,
                                    indicator.roe,
                                    indicator.adjusted_profit_to_profit).filter(

        valuation.code.in_(security),
        valuation.pb_ratio < 2,
        valuation.pe_ratio < 35,
        valuation.pe_ratio > 10,
        valuation.circulating_market_cap > 150,
        indicator.roe > 0.15,
        indicator.adjusted_profit_to_profit > 0.85,
        balance, total_current_assets/balance, total_current_liability > 1.2
    ))

    Stocks['Debt_Asset'] = Stocks['total_liability']/Stocks['total_assets']
    median = Stocks['Debt_Asset'].median()
    Codes = Stocks[Stocks['Debt_Asset'] > median].code
    return list(Codes)
