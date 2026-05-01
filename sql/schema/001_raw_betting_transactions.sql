create schema if not exists raw;

create table if not exists raw.bookmaker_bet_dump (
    ingestion_id bigserial primary key,
    source_file text not null,
    source_sheet text not null,
    source_row_number integer not null,
    ingested_at timestamptz not null default current_timestamp,
    refid text,
    source_uuid text,
    license text,
    bookmaker text,
    location text,
    state text,
    area text,
    wagering_provider text,
    sys_ver_no text,
    bet_date text,
    bet_time text,
    event_date text,
    event_time text,
    ticket_no text,
    event_category text,
    sport_event text,
    venue text,
    venue_state text,
    bet_type text,
    bet_method text,
    bet_details text,
    race_number text,
    runner_number text,
    runner_name text,
    bet_amount_win text,
    bet_amount_place text,
    win_price text,
    place_price text,
    customer_name text,
    betback_claim text,
    bet_information text,
    cancelled_flag text,
    time_cancelled text,
    bet_win_takeout text,
    bet_place_takeout text,
    horse_win_takeout text,
    horse_win_hold text,
    horse_place_takeout text,
    horse_place_hold text,
    race_hold text,
    betback_information text,
    betback_flag text,
    refund_flag text,
    placing_position text,
    win_deduction text,
    place_deduction text,
    win_result text,
    place_result text,
    win_payout_amount text,
    place_payout_amount text,
    paid_status text,
    bet_terminal text,
    raw_payload jsonb
);

create index if not exists idx_raw_bookmaker_bet_dump_refid
    on raw.bookmaker_bet_dump (refid);

create index if not exists idx_raw_bookmaker_bet_dump_ticket_no
    on raw.bookmaker_bet_dump (ticket_no);

create index if not exists idx_raw_bookmaker_bet_dump_source_uuid
    on raw.bookmaker_bet_dump (source_uuid);
