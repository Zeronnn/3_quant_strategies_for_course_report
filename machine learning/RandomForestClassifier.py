import jqdata
from sklearn.ensemble import RandomForestClassifier

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    g.model = RandomForestClassifier()  # 机器学习模型

def train_model(context):
    # 获取训练数据
    start_date = context.current_dt - datetime.timedelta(days=365)
    end_date = context.current_dt - datetime.timedelta(days=1)
    data = get_fundamentals(query(valuation).filter(valuation.code.in_(get_index_stocks('000300.XSHG'))))
    data = data.dropna()

    # 特征处理
    features = data[['pe_ratio', 'pb_ratio']]
    labels = data['code'].apply(lambda x: x in get_index_stocks('000300.XSHG'))

    # 训练机器学习模型
    g.model.fit(features, labels)

def select_stocks(context):
    # 获取选股数据
    data = get_fundamentals(query(valuation).filter(valuation.code.in_(get_index_stocks('000300.XSHG'))))
    data = data.dropna()

    # 特征处理
    features = data[['pe_ratio', 'pb_ratio']]

    # 使用机器学习模型进行预测
    predictions = g.model.predict(features)

    # 返回选出的股票列表
    return data.loc[predictions, 'code'].tolist()

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
