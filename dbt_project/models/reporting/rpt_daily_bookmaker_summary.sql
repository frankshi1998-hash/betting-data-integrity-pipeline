with duplicate_rows as (
    select
        bookmaker_name,
        bet_placed_at::date as report_date,
        count(*) as duplicate_extra_row_count
    from {{ ref('fct_bets') }}
    where is_duplicate_bet_key
    group by bookmaker_name, bet_placed_at::date
)

select
    b.bookmaker_name,
    b.bet_placed_at::date as report_date,
    count(*) as total_bet_rows,
    count(distinct b.bet_business_key) as distinct_bet_key_count,
    count(*) filter (where b.customer_key is not null) as named_customer_rows,
    count(*) filter (where b.is_cancelled is true) as cancelled_bet_rows,
    count(*) filter (where b.is_refunded is true) as refunded_bet_rows,
    coalesce(d.duplicate_extra_row_count, 0) as duplicate_extra_row_count,
    sum(coalesce(b.total_stake_amount, 0)) as total_stake_amount,
    sum(coalesce(b.total_payout_amount, 0)) as total_payout_amount,
    sum(coalesce(b.total_stake_amount, 0)) - sum(coalesce(b.total_payout_amount, 0)) as net_revenue_amount
from {{ ref('fct_bets') }} b
left join duplicate_rows d
  on d.bookmaker_name = b.bookmaker_name
 and d.report_date = b.bet_placed_at::date
group by b.bookmaker_name, b.bet_placed_at::date, d.duplicate_extra_row_count
