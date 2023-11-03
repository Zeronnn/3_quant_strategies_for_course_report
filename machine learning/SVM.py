import jqdata
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')
    g.model = SVC()  # 机器学习模型
    g.label_encoder = LabelEncoder()  # 标签编码器


def stock_filter(context, stock_list):
    # 过滤次新股,上市时间小于360天
    yesterday = context.previous_date
    stock_list = [stock for stock in stock_list if
                  not yesterday - get_security_info(stock).start_date < datetime.timedelta(days=360)]
    # 过滤科创版688开头,三板4开头,北交所8开头
    stock_list = [stock for stock in stock_list if stock[0:3] != '688' and stock[0] != '4' and stock[0] != '8']
    # 过滤停牌和'ST','*','退'等退市标签股票
    current_data = get_current_data()
    stock_list = [stock for stock in stock_list
                  if not current_data[stock].is_st
                  and not current_data[stock].paused
                  and 'ST' not in current_data[stock].name
                  and '*' not in current_data[stock].name
                  and '退' not in current_data[stock].name]
    return stock_list


def train_model(context):
    # 获取训练数据
    start_date = context.current_dt - datetime.timedelta(days=365)
    end_date = context.current_dt - datetime.timedelta(days=1)
    stocks = get_index_stocks('000300.XSHG') + get_index_stocks('000001.XSHG')  # 获取沪深300指数和上证指数的成分股
    stocks = stock_filter(context, stocks)
    data = get_fundamentals(query(valuation, indicator).filter(valuation.code.in_(stocks)))
    data = data.dropna()

    # 添加市值数据
    features = data[['pe_ratio', 'pb_ratio']]
    features['turnover_ratio'] = data['turnover_ratio']
    features['roa'] = data['roa']
    # features['inc_return'] = data['inc_return']
    # features['pcf_ratio'] = data['pcf_ratio']
    # features['circulating_market_cap'] = data['circulating_market_cap']

    # 添加财务指标数据
    features['roe'] = data['roe']
    features['eps'] = data['eps']
    # features['ps_ratio'] = data['ps_ratio']
    # features['net_profit_margin'] = data['net_profit_margin']
    # features['inc_net_profit_annual'] = data['inc_net_profit_annual']

    # 标签处理
    labels = data['code'].apply(
        lambda x: 'A' if x in get_index_stocks('000300.XSHG') else 'B')  # 二分类问题，A类为沪深300指数成分股，B类为其他股票
    g.label_encoder.fit(labels)  # 拟合标签编码器
    encoded_labels = g.label_encoder.transform(labels)  # 将标签转换为数值编码

    # 训练机器学习模型
    g.model.fit(features, encoded_labels)


def select_stocks(context):
    # 获取选股数据
    stocks = get_index_stocks('000300.XSHG') + get_index_stocks('000001.XSHG')  # 获取沪深300指数和上证指数的成分股
    stocks = stock_filter(context, stocks)
    data = get_fundamentals(query(valuation, indicator).filter(valuation.code.in_(stocks)))
    data = data.dropna()

    # 添加市值数据
    features = data[['pe_ratio', 'pb_ratio']]
    features['turnover_ratio'] = data['turnover_ratio']
    features['roa'] = data['roa']
    # features['inc_return'] = data['inc_return']

    # 添加财务指标数据
    features['roe'] = data['roe']
    features['eps'] = data['eps']

    # 使用机器学习模型进行预测
    predictions = g.model.predict(features)

    # 将预测结果转换为原始标签
    original_labels = g.label_encoder.inverse_transform(predictions)

    # 返回选出的股票列表
    return data.loc[original_labels == 'A', 'code'].tolist()


def handle_data(context, data):
    if context.current_dt.weekday() == 0:  # 每周一进行选股和调仓
        train_model(context)  # 训练机器学习模型
        selected_stocks = select_stocks(context)  # 选股
        adjust_portfolio(context, selected_stocks)  # 调仓


def adjust_portfolio(context, selected_stocks):
    # 平掉不在选股列表中的持仓股票
    for security in context.portfolio.positions:
        if security not in selected_stocks:
            order_target(security, 0)

    # 买入选股列表中的股票
    cash = context.portfolio.available_cash / len(selected_stocks)
    for security in selected_stocks:
        order_value(security, cash)
