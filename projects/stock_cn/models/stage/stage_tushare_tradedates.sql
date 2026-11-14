-- Trade calendar with the gap to the surrounding trading days
with latest as (

    -- Snapshots are full replays, only the newest one is valid
    select
        cal_date,
        nullif(trim(exchange), '') as exchange,
        is_open,
        snapshotdate
    from {{ source('tushare', 'tradedates') }}
    where snapshotdate = (select max(snapshotdate) from {{ source('tushare', 'tradedates') }})

),

neighbours as (

    -- Strictly before / after the row, so a trading day looks at the other trading days
    select
        *,
        max(case when is_open then cal_date end) over (
            partition by exchange
            order by cal_date
            rows between unbounded preceding and 1 preceding
        ) as prev_trade_date,
        min(case when is_open then cal_date end) over (
            partition by exchange
            order by cal_date
            rows between 1 following and unbounded following
        ) as next_trade_date
    from latest

)

select
    cal_date,
    exchange,
    is_open,
    snapshotdate,
    prev_trade_date,
    next_trade_date,

    -- Null at the head / tail of the calendar where there is no such trading day
    date_diff('day', cal_date, next_trade_date)::int as days_to_next_trade,
    date_diff('day', prev_trade_date, cal_date)::int as days_to_prev_trade

from neighbours
order by cal_date
