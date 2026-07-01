from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import (
    TRINO_ENABLED,
    TRINO_HOST,
    TRINO_PORT,
    TRINO_USER,
    TRINO_PASSWORD,
    TRINO_CATALOG,
    TRINO_SCHEMA,
    TRINO_HTTP_SCHEME,
    TRINO_SOURCE,
)


class TrinoUnavailableError(RuntimeError):
    pass


def _normalize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _sql_literal(value: Any) -> str:
    return "'{}'".format(str(value).replace("'", "''"))


def _sql_like(value: str) -> str:
    return "%{}%".format(str(value).replace("'", "''"))


@dataclass
class TrinoConfig:
    enabled: bool = TRINO_ENABLED
    host: str = TRINO_HOST
    port: int = TRINO_PORT
    user: str = TRINO_USER
    password: str = TRINO_PASSWORD
    catalog: str = TRINO_CATALOG
    schema: str = TRINO_SCHEMA
    http_scheme: str = TRINO_HTTP_SCHEME
    source: str = TRINO_SOURCE


class TrinoClient:
    def __init__(self, config: Optional[TrinoConfig] = None):
        self.config = config or TrinoConfig()

    def is_enabled(self) -> bool:
        return self.config.enabled

    def _connect(self):
        if not self.config.enabled:
            raise TrinoUnavailableError("Trino is disabled")

        try:
            import trino
        except ImportError as exc:
            raise TrinoUnavailableError(
                "Python package 'trino' is not installed"
            ) from exc

        auth = None
        if self.config.password:
            try:
                from trino.auth import BasicAuthentication

                auth = BasicAuthentication(self.config.user, self.config.password)
            except Exception as exc:
                raise TrinoUnavailableError(f"Failed to create Trino auth: {exc}") from exc

        try:
            return trino.dbapi.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                auth=auth,
                catalog=self.config.catalog,
                schema=self.config.schema,
                http_scheme=self.config.http_scheme,
                source=self.config.source,
            )
        except Exception as exc:
            raise TrinoUnavailableError(f"Failed to connect to Trino: {exc}") from exc

    def query_all(self, sql: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description or []]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def query_one(self, sql: str) -> Optional[Dict[str, Any]]:
        results = self.query_all(sql)
        return results[0] if results else None

    def get_exchange_rates(self) -> Dict[str, Any]:
        sql = f"""
        SELECT base, rates, update_time
        FROM {self.config.catalog}.{self.config.schema}.exchange_rates
        ORDER BY update_time DESC
        LIMIT 1
        """
        row = self.query_one(sql)
        if not row:
            return {
                "base": "CNY",
                "rates": {},
                "update_time": None,
            }

        rates = row.get("rates") or {}
        if not isinstance(rates, dict):
            rates = dict(rates)

        return {
            "base": row.get("base") or "CNY",
            "rates": rates,
            "update_time": _normalize_datetime(row.get("update_time")),
        }

    def get_brands(self, keyword: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        conditions = []
        if keyword:
            keyword_literal = keyword.replace("'", "''")
            conditions.append(
                f"(lower(name) LIKE lower('%{keyword_literal}%') OR lower(name_cn) LIKE lower('%{keyword_literal}%'))"
            )
        if category:
            category_literal = category.replace("'", "''")
            conditions.append(f"category = '{category_literal}'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
        SELECT brand_id, name, name_cn, logo, category
        FROM {self.config.catalog}.{self.config.schema}.brands
        {where_clause}
        ORDER BY name_cn
        """
        return self.query_all(sql)

    def get_categories(self) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT category_id, name, icon
        FROM {self.config.catalog}.{self.config.schema}.categories
        ORDER BY name
        """
        return self.query_all(sql)

    def search_products(
        self,
        keyword: Optional[str] = None,
        brand_id: Optional[str] = None,
        category_id: Optional[str] = None,
        country: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        offset = (page - 1) * page_size

        filters = []
        if keyword:
            keyword_literal = keyword.replace("'", "''")
            filters.append(
                f"(lower(s.name) LIKE lower('%{keyword_literal}%') OR lower(s.name_en) LIKE lower('%{keyword_literal}%') OR lower(s.article_no) LIKE lower('%{keyword_literal}%'))"
            )
        if brand_id:
            brand_literal = brand_id.replace("'", "''")
            filters.append(f"s.brand_id = '{brand_literal}'")
        if category_id:
            category_literal = category_id.replace("'", "''")
            filters.append(f"s.category_id = '{category_literal}'")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        sql = f"""
        WITH filtered_spu AS (
            SELECT s.*
            FROM {self.config.catalog}.{self.config.schema}.spus s
            {where_clause}
        ),
        price_stats AS (
            SELECT
                s.spu_id,
                COUNT(DISTINCT s.sku_id) AS sku_count,
                COUNT(DISTINCT p.country) AS country_count,
                MIN(CASE WHEN p.country = 'CN' THEN p.price END) AS min_cn_price,
                MIN(CASE WHEN p.country = 'JP' THEN p.price END) AS min_jp_price,
                MIN(p.price) AS min_price,
                MAX(p.price) AS max_price
            FROM {self.config.catalog}.{self.config.schema}.skus s
            LEFT JOIN {self.config.catalog}.{self.config.schema}.sku_prices p
                ON s.sku_id = p.sku_id
            WHERE s.spu_id IN (SELECT spu_id FROM filtered_spu)
            {f"AND p.country = '{country.replace("'", "''")}'" if country else ""}
            GROUP BY s.spu_id
        )
        SELECT
            s.spu_id,
            s.brand_id,
            s.brand_name,
            s.name,
            s.name_en,
            s.article_no,
            s.category_id,
            s.image,
            COALESCE(p.min_cn_price, 0) AS min_cn_price,
            COALESCE(p.min_jp_price, 0) AS min_jp_price,
            COALESCE(p.min_price, 0) AS min_price,
            COALESCE(p.max_price, 0) AS max_price,
            COALESCE(p.sku_count, 0) AS sku_count,
            COALESCE(p.country_count, 0) AS country_count
        FROM filtered_spu s
        LEFT JOIN price_stats p ON s.spu_id = p.spu_id
        ORDER BY s.created_at DESC
        LIMIT {int(page_size)} OFFSET {int(offset)}
        """
        list_rows = self.query_all(sql)

        total_sql = f"""
        SELECT COUNT(*) AS total
        FROM {self.config.catalog}.{self.config.schema}.spus s
        {where_clause}
        """
        total_row = self.query_one(total_sql)

        return {
            "list": list_rows,
            "total": int(total_row.get("total", 0)) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }

    def get_product_detail(self, spu_id: str) -> Optional[Dict[str, Any]]:
        spu_sql = f"""
        SELECT spu_id, brand_id, brand_name, name, name_en, article_no, category_id, image, description
        FROM {self.config.catalog}.{self.config.schema}.spus
        WHERE spu_id = '{spu_id.replace("'", "''")}'
        LIMIT 1
        """
        spu = self.query_one(spu_sql)
        if not spu:
            return None

        skus_sql = f"""
        SELECT sku_id, name, color, size
        FROM {self.config.catalog}.{self.config.schema}.skus
        WHERE spu_id = '{spu_id.replace("'", "''")}'
        ORDER BY created_at DESC
        """
        skus = self.query_all(skus_sql)
        sku_ids = [row["sku_id"] for row in skus if row.get("sku_id")]

        prices: List[Dict[str, Any]] = []
        if sku_ids:
            sku_id_list = ", ".join("'{}'".format(sku_id.replace("'", "''")) for sku_id in sku_ids)
            prices_sql = f"""
            SELECT id, sku_id, country, currency, price, stock, store, updated_at
            FROM {self.config.catalog}.{self.config.schema}.sku_prices
            WHERE sku_id IN ({sku_id_list})
            ORDER BY country, price
            """
            prices = self.query_all(prices_sql)

        sku_list: List[Dict[str, Any]] = []
        for sku in skus:
            sku_prices = [price for price in prices if price.get("sku_id") == sku.get("sku_id")]
            sku_list.append({
                "sku_id": sku.get("sku_id"),
                "name": sku.get("name"),
                "color": sku.get("color"),
                "size": sku.get("size"),
                "prices": sku_prices,
            })

        return {
            "spu": spu,
            "brand": {
                "brand_id": spu.get("brand_id"),
                "name": spu.get("brand_name"),
            },
            "category": {
                "category_id": spu.get("category_id"),
                "name": spu.get("category_id"),
            },
            "skus": sku_list,
        }

    def get_buyer_list(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        offset = (page - 1) * page_size
        conditions = []
        if country:
            conditions.append("country = {}".format(_sql_literal(country)))
        if city:
            conditions.append("city = {}".format(_sql_literal(city)))

        where_clause = "WHERE {}".format(" AND ".join(conditions)) if conditions else ""
        list_sql = """
        SELECT buyer_id, name, avatar, country, city, rating, orders, fee_rate, delivery_days, intro, created_at
        FROM {table}
        {where_clause}
        ORDER BY rating DESC, orders DESC, created_at DESC
        LIMIT {limit} OFFSET {offset}
        """.format(
            table="{}.{}.buyers".format(self.config.catalog, self.config.schema),
            where_clause=where_clause,
            limit=int(page_size),
            offset=int(offset),
        )
        total_sql = """
        SELECT COUNT(*) AS total
        FROM {table}
        {where_clause}
        """.format(
            table="{}.{}.buyers".format(self.config.catalog, self.config.schema),
            where_clause=where_clause,
        )
        return {
            "list": self.query_all(list_sql),
            "total": int(self.query_one(total_sql).get("total", 0)) if self.query_one(total_sql) else 0,
            "page": page,
            "page_size": page_size,
        }

    def get_buyer_detail(self, buyer_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT buyer_id, name, avatar, country, city, rating, orders, fee_rate, delivery_days, intro, created_at
        FROM {table}
        WHERE buyer_id = {buyer_id}
        LIMIT 1
        """.format(
            table="{}.{}.buyers".format(self.config.catalog, self.config.schema),
            buyer_id=_sql_literal(buyer_id),
        )
        return self.query_one(sql)

    def get_store_list(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        offset = (page - 1) * page_size
        conditions = []
        if country:
            conditions.append("country = {}".format(_sql_literal(country)))
        if city:
            conditions.append("city = {}".format(_sql_literal(city)))
        if type:
            conditions.append("type = {}".format(_sql_literal(type)))

        where_clause = "WHERE {}".format(" AND ".join(conditions)) if conditions else ""
        table_name = "{}.{}.stores".format(self.config.catalog, self.config.schema)
        list_sql = """
        SELECT store_id, name, type, country, city, address, rating, image, created_at
        FROM {table}
        {where_clause}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
        """.format(table=table_name, where_clause=where_clause, limit=int(page_size), offset=int(offset))
        total_sql = """
        SELECT COUNT(*) AS total
        FROM {table}
        {where_clause}
        """.format(table=table_name, where_clause=where_clause)
        total_row = self.query_one(total_sql)
        return {
            "list": self.query_all(list_sql),
            "total": int(total_row.get("total", 0)) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }

    def get_store_detail(self, store_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT store_id, name, type, country, city, address, rating, image, created_at
        FROM {table}
        WHERE store_id = {store_id}
        LIMIT 1
        """.format(
            table="{}.{}.stores".format(self.config.catalog, self.config.schema),
            store_id=_sql_literal(store_id),
        )
        return self.query_one(sql)

    def get_coupon_list(
        self,
        country: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        offset = (page - 1) * page_size
        conditions = []
        if country:
            conditions.append("country = {}".format(_sql_literal(country)))
        if store_id:
            conditions.append("store_id = {}".format(_sql_literal(store_id)))
        if status:
            conditions.append("status = {}".format(_sql_literal(status)))

        where_clause = "WHERE {}".format(" AND ".join(conditions)) if conditions else ""
        table_name = "{}.{}.coupons".format(self.config.catalog, self.config.schema)
        list_sql = """
        SELECT coupon_id, title, type, discount, threshold, country, store_id, store_name, expire_date, status, created_at
        FROM {table}
        {where_clause}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
        """.format(table=table_name, where_clause=where_clause, limit=int(page_size), offset=int(offset))
        total_sql = """
        SELECT COUNT(*) AS total
        FROM {table}
        {where_clause}
        """.format(table=table_name, where_clause=where_clause)
        total_row = self.query_one(total_sql)
        return {
            "list": self.query_all(list_sql),
            "total": int(total_row.get("total", 0)) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }

    def get_coupon_detail(self, coupon_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT coupon_id, title, type, discount, threshold, country, store_id, store_name, expire_date, status, created_at
        FROM {table}
        WHERE coupon_id = {coupon_id}
        LIMIT 1
        """.format(
            table="{}.{}.coupons".format(self.config.catalog, self.config.schema),
            coupon_id=_sql_literal(coupon_id),
        )
        return self.query_one(sql)

    def get_order_list(
        self,
        user_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        offset = (page - 1) * page_size
        conditions = []
        if user_id:
            conditions.append("user_id = {}".format(_sql_literal(user_id)))
        if buyer_id:
            conditions.append("buyer_id = {}".format(_sql_literal(buyer_id)))
        if status:
            conditions.append("status = {}".format(_sql_literal(status)))

        where_clause = "WHERE {}".format(" AND ".join(conditions)) if conditions else ""
        table_name = "{}.{}.orders".format(self.config.catalog, self.config.schema)
        list_sql = """
        SELECT order_id, user_id, buyer_id, buyer_name, spu_id, sku_id, product_name, product_image, sku_spec,
               quantity, original_price, original_currency, cny_price, fee_rate, fee_amount, shipping_fee,
               total_amount, status, country, store, remark, tracking_no, tracking_company, receiver_name,
               receiver_phone, receiver_address, created_at, updated_at, paid_at, shipped_at, completed_at, cancelled_at
        FROM {table}
        {where_clause}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
        """.format(table=table_name, where_clause=where_clause, limit=int(page_size), offset=int(offset))
        total_sql = """
        SELECT COUNT(*) AS total
        FROM {table}
        {where_clause}
        """.format(table=table_name, where_clause=where_clause)
        total_row = self.query_one(total_sql)
        return {
            "list": self.query_all(list_sql),
            "total": int(total_row.get("total", 0)) if total_row else 0,
            "page": page,
            "page_size": page_size,
        }

    def get_order_detail(self, order_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT order_id, user_id, buyer_id, buyer_name, spu_id, sku_id, product_name, product_image, sku_spec,
               quantity, original_price, original_currency, cny_price, fee_rate, fee_amount, shipping_fee,
               total_amount, status, country, store, remark, tracking_no, tracking_company, receiver_name,
               receiver_phone, receiver_address, created_at, updated_at, paid_at, shipped_at, completed_at, cancelled_at
        FROM {table}
        WHERE order_id = {order_id}
        LIMIT 1
        """.format(
            table="{}.{}.orders".format(self.config.catalog, self.config.schema),
            order_id=_sql_literal(order_id),
        )
        return self.query_one(sql)
