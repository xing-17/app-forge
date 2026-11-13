-- Weekly and yearly PSI share one schema: stack them and tidy each column
with stacked as (

    select
        'week' as record_source,
        * exclude ("date"),
        "date" as snapshotdate,
        null::bigint as snapshot_year
    from {{ source('nswvg', 'psi_week') }}

    union all by name

    select
        'year' as record_source,
        * exclude ("year"),
        null::date as snapshotdate,
        "year" as snapshotyear
    from {{ source('nswvg', 'psi_year') }}

),

tidy as (

    select
        record_source,
        snapshotdate,
        snapshotyear,
        download_time,
        file_name,
        -- Yearly archives replay old weekly files,
        -- the DDMMYYYY suffix says which revision a line is
        try_strptime(
            regexp_extract(file_name, '_([0-9]{8})\.DAT$', 1), '%d%m%Y'
        )::date as revision_date,
        sale_counter,
        interest_of_sale,
        nullif(trim(district_code), '') as district_code,
        nullif(trim(property_id), '') as property_id,
        nullif(trim(property_name), '') as property_name,
        nullif(trim(unit_number), '') as unit_number,
        nullif(trim(house_number), '') as house_number,
        nullif(trim(street_name), '') as street_name,
        nullif(trim(locality), '') as locality,
        nullif(trim(dimensions), '') as dimensions,
        nullif(trim(zone_code), '') as zone_code,
        nullif(trim(nature_of_property), '') as nature_of_property,
        nullif(upper(trim(primary_purpose)), '') as primary_purpose,
        nullif(trim(strata_lot_number), '') as strata_lot_number,
        nullif(trim(component_code), '') as component_code,
        nullif(trim(sale_code), '') as sale_code,
        nullif(trim(dealing_number), '') as dealing_number,
        nullif(trim(land_description), '') as land_description,

        -- Archive rows carry '0' and short codes for unknown postcodes
        case 
            when regexp_full_match(trim(postcode), '[0-9]{4}') then trim(postcode) 
            else null
        end as postcode,

        -- H is hectares, 
        -- M is square metres, 
        -- anything else is unusable
        case
            when area <= 0 then null
            when area_type = 'H' then area * 10000
            when area_type = 'M' then area
        end as area_sqm,

        -- NSW PSI starts in 1990
        -- later dates are keying errors
        case 
            when contract_date between date '1990-01-01' and current_date then contract_date 
            else null
        end as contract_date,
        case 
            when settlement_date between date '1990-01-01' and current_date then settlement_date 
            else null
        end as settlement_date,

        case when purchase_price > 0 then purchase_price end as purchase_price

    from stacked
    where true
        and contract_date is not null               -- Ensure contract date is available
        and settlement_date is not null             -- Ensure settlement date is available
        and contract_date >= date '2000-01-01'      -- Records before 2000 is out of scope
        and settlement_date >= date '2000-01-01'    -- Records before 2000 is out of scope
)

select
    * replace (
        case 
            when settlement_date < contract_date then null 
            else settlement_date 
        end as settlement_date
    ),

    -- Under 10k is nominal consideration (gifts, transfers)
    -- it might not be a market price hence flagged as nominal price
    purchase_price < 10000 as is_nominal_price

from tidy
