# Power BI Dashboard Specifications: Instacart Customer Retention & Behavioral Churn Intelligence

This document outlines the detailed specifications for building an interactive Power BI dashboard to visualize customer retention and behavioral churn insights derived from the Instacart dataset.

## 1. Data Model Diagram Description

The Power BI data model has three tables (import all three CSVs from the `data/` folder):

-   **`user_segments`** (`instacart_user_segments.csv`): one row per customer with RFM scores, `recency_days` and the derived `Customer_Segment`. Key: `user_id`.
-   **`orders`** (`orders.csv`): one row per order (`order_id`, `user_id`, `order_number`, `order_date`, `order_dow`, `order_hour_of_day`, `days_since_prior_order`). Key: `order_id`.
-   **`order_products`** (`order_products.csv`): one row per item in an order. Links to `orders` on `order_id`.

**Relationships** (all single-direction, 1-to-many, filter flows left to right):
`user_segments[user_id]` → `orders[user_id]` and `orders[order_id]` → `order_products[order_id]`.

**Notes:** `order_dow` is 0 = Monday ... 6 = Sunday. `recency_days` = days from the user's last order to the snapshot date (latest order date + 1). Mark `orders[order_date]` as a Date column.

## 2. Explicit DAX Measures

-   **`Total Users`**
    ```dax
    Total Users = DISTINCTCOUNT(user_segments[user_id])
    ```

-   **`Churn Rate %`** (segment-based proxy: share of users in the Churned / Dormant segment)
    ```dax
    Churn Rate % =
    DIVIDE(
        CALCULATE(COUNTROWS(user_segments), user_segments[Customer_Segment] = "Churned / Dormant"),
        COUNTROWS(user_segments)
    )
    ```

-   **`Avg Basket Size (Items)`**
    ```dax
    Avg Basket Size (Items) =
    DIVIDE(COUNTROWS(order_products), DISTINCTCOUNT(orders[order_id]))
    ```

-   **`At Risk User Count`**
    ```dax
    At Risk User Count =
    CALCULATE(COUNTROWS(user_segments), user_segments[Customer_Segment] = "At Risk (High Volume)")
    ```

-   **`Avg Recency (Days)`**
    ```dax
    Avg Recency (Days) = AVERAGE(user_segments[recency_days])
    ```

## 3. Layout & Visual Map

The dashboard will be structured to provide a clear and actionable overview of customer retention and churn. The layout will include:

-   **Executive Header KPI Cards**:
    -   **Location**: Top section of the dashboard.
    -   **Content**: Display key metrics such as `Total Users`, `Churn Rate %`, `Avg Basket Size (Items)`, and `At Risk User Count` for quick executive overview.
    -   **Visual Type**: Single value cards.

-   **Donut Chart: User Distribution by `Customer_Segment`**:
    -   **Location**: Prominent position, e.g., top-left or top-center.
    -   **Content**: Show the proportion of users in each `Customer_Segment` (Loyal Power Users, At Risk (High Volume), Churned / Dormant, Occasional Shoppers).
    -   **Visual Type**: Donut Chart.
    -   **Interaction**: Clicking on a segment should filter other visuals to show data for that segment.

-   **Scatter Plot: Recency vs. Frequency (Color-coded by Segment)**:
    -   **Location**: Central part of the dashboard.
    -   **X-axis**: `recency_days` (from `user_segments`)
    -   **Y-axis**: `frequency` (from `user_segments`)
    -   **Color Legend**: `Customer_Segment` (from `user_segments`)
    -   **Visual Type**: Scatter Plot.
    -   **Interaction**: Tooltips should display `user_id` and segment details on hover.

-   **Heatmap (Matrix) / Bar Chart: Peak Order Hours by Day of Week**:
    -   **Location**: Bottom section of the dashboard.
    -   **Content**: Visualize the distribution of `order_hour_of_day` across `order_dow` (Day of Week), potentially broken down by churn risk status (e.g., 'At Risk' vs. 'Loyal'). Use a Matrix visual with `order_dow` as rows, `order_hour_of_day` as columns, count of `order_id` as values and conditional background colour.
    -   **Visual Type**: Heatmap (preferred for density) or Bar Chart (if specific hour/day counts are more critical).
    -   **Data Source**: Derived from the `orders` table and potentially joined with `user_segments` for churn risk status.
