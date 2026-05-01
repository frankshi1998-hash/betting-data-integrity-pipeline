create or replace view stage.bookmaker_bets_clean as
select
    ingestion_id,
    source_file,
    source_sheet,
    source_row_number,
    ingested_at,
    util.clean_text(refid) as source_refid,
    util.clean_text(source_uuid) as source_uuid,
    util.clean_text(license) as license,
    util.clean_text(bookmaker) as bookmaker_name,
    util.clean_text(location) as location_name,
    util.clean_text(state) as state_code,
    util.clean_text(area) as area_name,
    util.clean_text(wagering_provider) as wagering_provider,
    util.clean_text(sys_ver_no) as system_version,
    util.parse_source_timestamp(bet_date, bet_time) as bet_placed_at,
    util.parse_source_timestamp(event_date, event_time) as event_scheduled_at,
    util.clean_text(ticket_no) as ticket_no,
    util.clean_text(event_category) as event_category,
    util.clean_text(sport_event) as sport_event_name,
    util.clean_text(venue) as venue_name,
    util.clean_text(venue_state) as venue_state_code,
    util.clean_text(bet_type) as bet_type,
    util.clean_text(bet_method) as bet_method,
    util.clean_text(bet_details) as bet_details,
    util.parse_integer(race_number) as race_number,
    util.parse_integer(runner_number) as runner_number,
    util.clean_text(runner_name) as runner_name,
    util.parse_money(bet_amount_win) as stake_win_amount,
    util.parse_money(bet_amount_place) as stake_place_amount,
    coalesce(util.parse_money(bet_amount_win), 0) + coalesce(util.parse_money(bet_amount_place), 0) as total_stake_amount,
    util.parse_decimal(win_price) as win_price,
    util.parse_decimal(place_price) as place_price,
    util.clean_text(customer_name) as customer_name,
    util.clean_text(betback_claim) as betback_claim,
    util.clean_text(bet_information) as bet_information,
    util.parse_boolean_flag(cancelled_flag) as is_cancelled,
    util.parse_source_timestamp(bet_date, time_cancelled) as cancelled_at,
    util.parse_decimal(bet_win_takeout) as bet_win_takeout,
    util.parse_decimal(bet_place_takeout) as bet_place_takeout,
    util.parse_decimal(horse_win_takeout) as horse_win_takeout,
    util.parse_decimal(horse_win_hold) as horse_win_hold,
    util.parse_decimal(horse_place_takeout) as horse_place_takeout,
    util.parse_decimal(horse_place_hold) as horse_place_hold,
    util.parse_decimal(race_hold) as race_hold,
    util.clean_text(betback_information) as betback_information,
    util.parse_boolean_flag(betback_flag) as is_betback,
    util.parse_boolean_flag(refund_flag) as is_refunded,
    util.parse_integer(placing_position) as placing,
    util.parse_decimal(win_deduction) as win_deduction,
    util.parse_decimal(place_deduction) as place_deduction,
    util.parse_decimal(win_result) as win_result,
    util.parse_decimal(place_result) as place_result,
    util.parse_money(win_payout_amount) as win_payout_amount,
    util.parse_money(place_payout_amount) as place_payout_amount,
    coalesce(util.parse_money(win_payout_amount), 0) + coalesce(util.parse_money(place_payout_amount), 0) as total_payout_amount,
    util.clean_text(paid_status) as paid_status,
    util.clean_text(bet_terminal) as bet_terminal,
    raw_payload,
    case
        when util.clean_text(refid) is null then true
        else false
    end as missing_refid_flag,
    case
        when util.parse_money(bet_amount_win) is null
             and util.parse_money(bet_amount_place) is null then true
        else false
    end as missing_stake_flag,
    case
        when coalesce(util.parse_money(bet_amount_win), 0) + coalesce(util.parse_money(bet_amount_place), 0) < 0 then true
        else false
    end as negative_stake_flag
from raw.bookmaker_bet_dump;
