{% macro get_current_snapshotdate() %}
    strftime(current_date, '%Y-%m-%d')
{% endmacro %}
