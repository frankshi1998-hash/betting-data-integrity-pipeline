with normalized_customer_activity as (
    select
        md5({{ normalize_customer_name('customer_name') }}) as customer_key,
        {{ normalize_customer_name('customer_name') }} as customer_name_normalized,
        customer_name as customer_name_raw,
        bookmaker_name,
        state_code,
        bet_placed_at,
        total_stake_amount,
        total_payout_amount
    from {{ ref('stg_bookmaker_bets') }}
    where customer_name is not null
)

select
    customer_key,
    customer_name_normalized,
    min(customer_name_raw) as customer_name_example,
    count(*) as bet_count,
    count(distinct bookmaker_name) as bookmaker_count,
    count(distinct state_code) as state_count,
    min(bet_placed_at) as first_bet_at,
    max(bet_placed_at) as last_bet_at,
    sum(coalesce(total_stake_amount, 0)) as total_stake_amount,
    sum(coalesce(total_payout_amount, 0)) as total_payout_amount
from normalized_customer_activity
group by customer_key, customer_name_normalized
