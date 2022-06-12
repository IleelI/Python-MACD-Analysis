import sys
import pandas as pd
import matplotlib.pyplot as plt


EMA = 'EMA'
DATE = 'Date'
CLOSE = 'Close'
INTERSECT = 'Intersect'
MIN_ENTRIES = 120


def get_soothing_constant(period_length):
    return 2 / (period_length + 1) if isinstance(period_length, int) else None


def get_ema(current_value, previous_ema, period_length):
    soothing_constant = get_soothing_constant(period_length)
    return current_value * soothing_constant + previous_ema * (1 - soothing_constant)


def get_ema_aray(input_data, value_column_name, period_length):
    output_data = pd.DataFrame(data={
        DATE: [input_data[DATE][period_length - 1]],
        EMA: [input_data[value_column_name][:period_length].mean()]
    })
    data = input_data[:][period_length:].reset_index(drop=True)
    for data in data.itertuples():
        curr_value = getattr(data, value_column_name)
        prev_ema = output_data[EMA][data.Index]
        df = pd.DataFrame(data={DATE: [data.Date], EMA: [get_ema(curr_value, prev_ema, period_length)]})
        output_data = pd.concat([output_data, df], ignore_index=True)
    return output_data


def even_data(larger_data, smaller_data):
    size_difference = len(larger_data) - len(smaller_data)
    return larger_data[:][size_difference:]


class MACDPointer:
    def __init__(self):
        self.data = None
        self.shorter_period_ema = None
        self.greater_period_ema = None
        self.macd_data = None
        self.signal_data = None
        self.intersect_points = None

    def load_csv_data(self, file):
        try:
            self.data = pd.read_csv(file)
            # convert string values to datetime type from pandas library
            self.data[DATE] = pd.to_datetime(self.data[DATE], format='%Y-%m-%d')
            if len(self.data) < MIN_ENTRIES:
                return -1
            else:
                return 0
        except Exception as e:
            return -1

    def set_ema_data(self):
        shorter_period_ema = get_ema_aray(self.data, CLOSE, 12)
        greater_period_ema = get_ema_aray(self.data, CLOSE, 26)
        self.shorter_period_ema = shorter_period_ema
        self.greater_period_ema = greater_period_ema

    def set_macd_data(self):
        period_difference = len(self.shorter_period_ema) - len(self.greater_period_ema)
        macd_data = self.shorter_period_ema[:][period_difference:].reset_index(drop=True)
        macd_data[EMA] = macd_data[EMA] - self.greater_period_ema[EMA]
        self.macd_data = macd_data

    def set_signal_data(self):
        signal_data = self.macd_data
        signal_data = get_ema_aray(signal_data, EMA, 9)
        self.signal_data = signal_data

    def init_macd_pointer_data(self):
        self.set_ema_data()
        self.set_macd_data()
        self.set_signal_data()

    def get_number_of_entries(self):
        MAX_ENTRIES = len(self.data)
        print('Welcome, please enter number of entries you wish to analise.')
        print(f'Acceptable value start from {MIN_ENTRIES} to {MAX_ENTRIES}.')
        valid_input = False
        user_input = 0
        while not valid_input:
            user_input = int(input('Enter number of entries to load:\t'))
            if MIN_ENTRIES <= user_input <= MAX_ENTRIES:
                valid_input = True
            else:
                print(f'Invalid value, please enter value from range: [{MIN_ENTRIES}, {MAX_ENTRIES}]\n')
        self.data = self.data[:][:user_input]

    def __str__(self):
        return f'Shorter Period: {len(self.shorter_period_ema)}\n' \
               f'Greater Period: {len(self.greater_period_ema)}\n' \
               f'MACD: {len(self.macd_data)}\n' \
               f'SIGNAL: {len(self.signal_data)}'


def get_date_tick_step(data_size):
    if data_size < MIN_ENTRIES * 2:
        return 5
    elif data_size <= MIN_ENTRIES * 4:
        return 10
    elif data_size <= MIN_ENTRIES * 8:
        return 15
    elif data_size <= MIN_ENTRIES * 12:
        return 20
    elif data_size <= MIN_ENTRIES * 16:
        return 25
    else:
        return 30


def plot_macd_pointer(data):
    data_size = len(data.data)
    x_tick_step = get_date_tick_step(data_size)
    data_offset = data_size - len(data.signal_data)
    fig_height = 16
    fig_width = (data_size - data_offset) // x_tick_step
    fig, axes = plt.subplots(figsize=(fig_width, fig_height), nrows=2, ncols=1, constrained_layout=True)

    date_data = data.data[DATE][data_offset:]
    stock_close_data = data.data[CLOSE][data_offset:]
    axes[0].grid()
    axes[0].set_title(f'Bitcoin value ({data_size - data_offset} days)')
    axes[0].set_xlabel(f'Time ({x_tick_step} days)')
    axes[0].set_ylabel('Close value ($)')
    axes[0].plot(date_data, stock_close_data, 'k-', label='BTC')
    axes[0].legend(loc='best')
    axes[0].set_xticks(date_data[::x_tick_step])
    axes[0].set_xticklabels(date_data[::x_tick_step].dt.to_period('D'), rotation=90)

    macd_signal_data_offset = len(data.macd_data) - len(data.signal_data)
    macd_ema_data = data.macd_data[EMA][macd_signal_data_offset:]
    signal_ema_data = data.signal_data[EMA][:]
    axes[1].grid()
    axes[1].set_title(f'MACD ({data_size - data_offset} days)')
    axes[1].set_xlabel(f'Time ({x_tick_step} days)')
    axes[1].set_ylabel('EMA')
    axes[1].plot(date_data, macd_ema_data, 'b-', label='MACD')
    axes[1].legend(loc='best')
    axes[1].plot(date_data, signal_ema_data, 'r--', label='SIGNAL')
    axes[1].legend(loc='best')
    axes[1].set_xticks(date_data[::x_tick_step])
    axes[1].set_xticklabels(date_data[::x_tick_step].dt.to_period('D'), rotation=90)

    plt.show()
    fig.savefig(f'macd-{data_size}.png', dpi=fig.dpi)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise ValueError('Please provide file path to csv file with stock data.')
    else:
        file_path = sys.argv[1]
        stock_data = MACDPointer()
        if stock_data.load_csv_data(file_path) == 0:
            stock_data.get_number_of_entries()
            stock_data.init_macd_pointer_data()
            plot_macd_pointer(stock_data)
        else:
            print(f'Data sample is too small or provided path is invalid,'
                  f' please provide correct data with at lease {MIN_ENTRIES} entries!')
