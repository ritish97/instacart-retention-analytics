-- ------------------------------------------------------------------------------
-- 1. SCHEMA
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS order_products CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS user_segments CASCADE;

CREATE TABLE user_segments (
    user_id            INT PRIMARY KEY,
    recency_days       INT,
    avg_lapse          FLOAT,          -- NULL for users with a single order
    frequency          INT,
    total_items_bought INT,
    R_score            INT,
    F_score            INT,
    M_score            INT,
    Customer_Segment   VARCHAR(50)
);

CREATE TABLE orders (
    order_id               INT PRIMARY KEY,
    user_id                INT REFERENCES user_segments(user_id),
    order_number           INT,
    order_date             DATE,
    order_dow              INT,
    order_hour_of_day      INT,
    days_since_prior_order FLOAT       -- NULL for each user's first order
);

CREATE TABLE order_products (
    order_id          INT REFERENCES orders(order_id),
    product_id        INT,
    add_to_cart_order INT,
    reordered         INT,
    PRIMARY KEY (order_id, product_id)
);
-- ------------------------------------------------------------------------------
-- 3. ANALYTICAL QUERIES
-- ------------------------------------------------------------------------------
-- Query 1: Segment breakdown
SELECT
    Customer_Segment,
    COUNT(user_id)                       AS total_users,
    ROUND(AVG(frequency)::numeric, 2)          AS avg_orders_per_user,
    ROUND(AVG(total_items_bought)::numeric, 2) AS avg_items_bought,
    ROUND(AVG(recency_days)::numeric, 2)       AS avg_days_since_last_order
FROM user_segments
GROUP BY Customer_Segment
ORDER BY total_users DESC;
-- Query 2: Rolling interval lag analysis (churn signal)
-- Flags an order when its gap is more than 25% longer than the average of the user's previous 3 gaps
-- (current row excluded). The 25% threshold filters out ordinary day-to-day noise.
WITH RollingLapse AS (
    SELECT
        user_id,
        order_number,
        days_since_prior_order,
        AVG(days_since_prior_order) OVER (
            PARTITION BY user_id
            ORDER BY order_number
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS prev_avg_lapse
    FROM orders
    WHERE days_since_prior_order IS NOT NULL
)
SELECT
    r.user_id,
    u.Customer_Segment,
    r.order_number,
    r.days_since_prior_order,
    ROUND(r.prev_avg_lapse::numeric, 2) AS prev_avg_lapse,
    CASE
        WHEN r.prev_avg_lapse IS NULL                        THEN 'Insufficient history'
        WHEN r.days_since_prior_order > 1.25 * r.prev_avg_lapse THEN 'Expanding Interval (Risk)'
        ELSE 'Stable/Improving'
    END AS churn_signal
FROM RollingLapse r
JOIN user_segments u ON r.user_id = u.user_id
ORDER BY r.user_id, r.order_number;
-- Query 2b: Per-user interval trend (stronger churn signal than the per-order flag above)
-- Compares each user's last 3 gaps with all their earlier gaps. Needs at least 3 earlier gaps.
WITH Gaps AS (
    SELECT
        user_id,
        days_since_prior_order,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_number DESC) AS gaps_from_end
    FROM orders
    WHERE days_since_prior_order IS NOT NULL
),
Trend AS (
    SELECT
        user_id,
        AVG(CASE WHEN gaps_from_end <= 3 THEN days_since_prior_order END) AS recent_avg_gap,
        AVG(CASE WHEN gaps_from_end >  3 THEN days_since_prior_order END) AS earlier_avg_gap,
        COUNT(CASE WHEN gaps_from_end > 3 THEN 1 END)                      AS earlier_gaps
    FROM Gaps
    GROUP BY user_id
)
SELECT
    t.user_id,
    u.Customer_Segment,
    ROUND(t.earlier_avg_gap::numeric, 2) AS earlier_avg_gap,
    ROUND(t.recent_avg_gap::numeric, 2)  AS recent_avg_gap,
    CASE WHEN t.recent_avg_gap > 1.25 * t.earlier_avg_gap
         THEN 'Expanding Interval (Risk)' ELSE 'Stable/Improving' END AS churn_signal
FROM Trend t
JOIN user_segments u ON t.user_id = u.user_id
WHERE t.earlier_gaps >= 3
ORDER BY t.user_id;
-- Query 3: Peak ordering hour for each segment and day of week
-- ROW_NUMBER (not RANK) so exactly one row is returned per segment/day; ties go to the earlier hour.
WITH HourCounts AS (
    SELECT
        u.Customer_Segment,
        o.order_dow,
        o.order_hour_of_day,
        COUNT(o.order_id) AS order_count,
        ROW_NUMBER() OVER (
            PARTITION BY u.Customer_Segment, o.order_dow
            ORDER BY COUNT(o.order_id) DESC, o.order_hour_of_day
        ) AS hour_rank
    FROM orders o
    JOIN user_segments u ON o.user_id = u.user_id
    GROUP BY u.Customer_Segment, o.order_dow, o.order_hour_of_day
)
SELECT
    Customer_Segment,
    order_dow,
    order_hour_of_day AS peak_order_hour,
    order_count
FROM HourCounts
WHERE hour_rank = 1
ORDER BY Customer_Segment, order_dow;
