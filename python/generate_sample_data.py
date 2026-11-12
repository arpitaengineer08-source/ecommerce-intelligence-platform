"""
Synthetic data generator that mimics the schema of the Olist Brazilian E-Commerce dataset.

WHY: The real Olist dataset (Kaggle) must be downloaded manually (licence + login).
This generator lets the whole platform run end-to-end out of the box. All files use the
exact Olist file and column names, so you can later drop the real CSVs into data/raw/
and re-run the pipeline with ZERO code changes.

The generated data deliberately contains realistic business patterns (growth, Black Friday
spike, regional delivery gaps, late-delivery -> low-rating effect, declining/growing
categories) plus a few intentional data-quality defects for the cleaning step to catch.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_RAW, OLIST_FILES, RANDOM_SEED, STATES  # noqa: E402

# pt_name: (en_name, median_price, popularity, trend_slope)  trend>0 growing, <0 declining
CATEGORIES = {
    "beleza_saude": ("health_beauty", 95, 10, 0.55),
    "relogios_presentes": ("watches_gifts", 180, 6, 0.25),
    "cama_mesa_banho": ("bed_bath_table", 85, 11, 0.05),
    "esporte_lazer": ("sports_leisure", 100, 8, 0.2),
    "informatica_acessorios": ("computers_accessories", 90, 8, 0.1),
    "moveis_decoracao": ("furniture_decor", 80, 8, -0.1),
    "utilidades_domesticas": ("housewares", 60, 7, 0.0),
    "cool_stuff": ("cool_stuff", 120, 4, 0.1),
    "automotivo": ("auto", 90, 4, 0.0),
    "ferramentas_jardim": ("garden_tools", 85, 4, -0.15),
    "brinquedos": ("toys", 70, 4, -0.45),
    "perfumaria": ("perfumery", 95, 4, 0.3),
    "telefonia": ("telephony", 60, 4, 0.15),
    "bebes": ("baby", 90, 3.5, 0.0),
    "papelaria": ("stationery", 40, 2.5, -0.7),
    "fashion_bolsas_e_acessorios": ("fashion_bags_accessories", 110, 2.5, 0.35),
    "eletronicos": ("electronics", 120, 2.5, 0.3),
    "pet_shop": ("pet_shop", 75, 2, 0.4),
    "eletrodomesticos": ("home_appliances", 280, 2, 0.0),
    "livros_interesse_geral": ("books_general_interest", 45, 1.5, -0.8),
    "moveis_escritorio": ("office_furniture", 260, 1.5, -0.3),
    "pcs": ("computers", 1500, 0.6, -0.2),
}
STATE_W = {"SP": 41.5, "RJ": 12.9, "MG": 11.7, "RS": 5.5, "PR": 5.1, "SC": 3.7, "BA": 3.4, "DF": 2.1,
           "GO": 2.0, "ES": 2.0, "PE": 1.7, "CE": 1.3, "PA": 1.0, "MT": 0.9, "MA": 0.7, "MS": 0.7,
           "PB": 0.55, "PI": 0.5, "RN": 0.5, "AL": 0.4, "SE": 0.35, "TO": 0.3, "RO": 0.25,
           "AM": 0.15, "AC": 0.08, "AP": 0.07, "RR": 0.05}

COMMENTS_BAD_LATE = ["Produto chegou com muito atraso", "Entrega atrasou e ninguem avisou",
                     "Ainda nao recebi o produto", "Atraso na entrega, pessimo"]
COMMENTS_BAD_OTHER = ["Produto veio quebrado", "Qualidade ruim, nao recomendo", "Produto diferente do anunciado",
                      "Veio com defeito", "Vendedor nao respondeu", "Faltou item no pedido"]
COMMENTS_MID = ["Produto ok, mas demorou um pouco", "Atende, mas esperava mais", "Razoavel pelo preco"]
COMMENTS_GOOD = ["Excelente produto, recomendo", "Entrega rapida, tudo certo", "Chegou antes do prazo",
                 "Muito bom, qualidade otima", "Super recomendo a loja", "Produto conforme descrito"]


def _hex_ids(rng, n, prefix=0):
    return [f"{prefix:04x}{int(rng.integers(0, 2**60)):015x}{i:013x}" for i in range(n)]


def generate(out_dir: Path = DATA_RAW, n_orders: int = 22000, seed: int = RANDOM_SEED) -> dict:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- calendar & demand
    days = pd.date_range("2017-01-01", "2018-08-31")
    t = np.arange(len(days)) / len(days)
    season = np.ones(len(days))
    season[(days.year == 2017) & (days.month == 11)] *= 1.9  # Black Friday
    season[(days.year == 2017) & (days.month == 12)] *= 1.1
    season[days.month == 5] *= 1.1
    wk = np.where(days.dayofweek < 5, 1.12, 0.8)
    w = (0.3 + 1.5 * t) * season * wk
    w /= w.sum()
    day_idx = rng.choice(len(days), size=n_orders, p=w)
    hour_w = np.array([1, .5, .3, .2, .2, .4, 1, 2, 3.5, 4.5, 5.5, 5.5, 5, 5, 5.5, 5.5, 5.5, 5, 5, 5.5, 6, 6, 5, 3])
    hours = rng.choice(24, size=n_orders, p=hour_w / hour_w.sum())
    purchase = (days[day_idx] + pd.to_timedelta(hours, "h") + pd.to_timedelta(rng.integers(0, 3600, n_orders), "s"))
    purchase = pd.DatetimeIndex(np.sort(purchase.values))
    month_idx = ((purchase.year - 2017) * 12 + purchase.month - 1).values

    # ---------------------------------------------------------------- customers
    state_keys = list(STATE_W)
    state_p = np.array(list(STATE_W.values())); state_p /= state_p.sum()
    uniq_of_order = np.empty(n_orders, dtype=int)
    pool: list[int] = []
    n_unique = 0
    for i in range(n_orders):
        if pool and rng.random() < 0.045:
            j = pool[int(rng.integers(len(pool)))]
        else:
            j = n_unique
            n_unique += 1
        uniq_of_order[i] = j
        pool.append(j)
    u_ids = _hex_ids(rng, n_unique, 0xC1)
    u_state = rng.choice(state_keys, size=n_unique, p=state_p)
    u_city = [f"{s.lower()}_city_{int(k)}" for s, k in zip(u_state, rng.integers(0, 8, n_unique))]
    u_zip = rng.integers(1000, 99999, n_unique)
    order_ids = _hex_ids(rng, n_orders, 0x0D)
    cust_ids = _hex_ids(rng, n_orders, 0xC2)
    customers = pd.DataFrame({
        "customer_id": cust_ids,
        "customer_unique_id": [u_ids[j] for j in uniq_of_order],
        "customer_zip_code_prefix": u_zip[uniq_of_order],
        "customer_city": [u_city[j] for j in uniq_of_order],
        "customer_state": u_state[uniq_of_order],
    })

    # ---------------------------------------------------------------- sellers
    n_sellers = 600
    s_state = rng.choice(state_keys, size=n_sellers, p=np.array([60 if s == "SP" else 4 if s in ("RJ", "MG", "PR", "SC", "RS") else 0.6 for s in state_keys]) / sum(60 if s == "SP" else 4 if s in ("RJ", "MG", "PR", "SC", "RS") else 0.6 for s in state_keys))
    s_ids = _hex_ids(rng, n_sellers, 0x5E)
    sellers = pd.DataFrame({"seller_id": s_ids, "seller_zip_code_prefix": rng.integers(1000, 99999, n_sellers),
                            "seller_city": [f"{s.lower()}_city_{int(k)}" for s, k in zip(s_state, rng.integers(0, 8, n_sellers))],
                            "seller_state": s_state})
    s_handling = rng.uniform(1.2, 3.8, n_sellers)
    s_delay_mult = np.where(rng.random(n_sellers) < 0.10, rng.uniform(1.6, 2.4, n_sellers), rng.uniform(0.85, 1.15, n_sellers))
    s_size = rng.pareto(1.3, n_sellers) + 0.2
    s_size /= s_size.sum()

    # ---------------------------------------------------------------- products
    cat_pt = list(CATEGORIES)
    pop = np.array([CATEGORIES[c][2] for c in cat_pt], float)
    n_products = 3500
    p_cat = rng.choice(len(cat_pt), size=n_products, p=pop / pop.sum())
    p_ids = _hex_ids(rng, n_products, 0x9A)
    med = np.array([CATEGORIES[cat_pt[c]][1] for c in p_cat], float)
    base_price = np.clip(rng.lognormal(np.log(med), 0.6), 6, 3500).round(2)
    weight = np.clip(rng.lognormal(6.5, 0.9, n_products), 80, 30000).astype(int)
    p_seller = rng.choice(n_sellers, size=n_products, p=s_size)
    products = pd.DataFrame({
        "product_id": p_ids,
        "product_category_name": [cat_pt[c] for c in p_cat],
        "product_name_lenght": rng.integers(20, 70, n_products),
        "product_description_lenght": rng.integers(100, 2500, n_products),
        "product_photos_qty": rng.integers(1, 8, n_products),
        "product_weight_g": weight,
        "product_length_cm": rng.integers(10, 80, n_products),
        "product_height_cm": rng.integers(2, 50, n_products),
        "product_width_cm": rng.integers(8, 60, n_products),
    })
    products.loc[rng.random(n_products) < 0.015, "product_category_name"] = np.nan  # defect: missing category
    prod_by_cat = {c: np.where(p_cat == c)[0] for c in range(len(cat_pt))}
    prod_w = {c: (lambda a: a / a.sum())(1.0 / (np.arange(1, len(ix) + 1) ** 0.9)) for c, ix in prod_by_cat.items()}
    slopes = np.array([CATEGORIES[c][3] for c in cat_pt])
    holiday_boost = np.array([1.6 if CATEGORIES[c][0] in ("toys", "watches_gifts", "electronics", "perfumery", "cool_stuff") else 1.15 for c in cat_pt])

    def cat_weights(m):
        tt = m / 19.0
        wts = pop * np.clip(1 + slopes * (tt - 0.5) * 2, 0.15, None)
        if m in (10, 11):  # Nov/Dec 2017
            wts = wts * holiday_boost
        return wts / wts.sum()
    cw = {m: cat_weights(m) for m in range(20)}

    # ---------------------------------------------------------------- order items
    n_items = rng.choice([1, 2, 3, 4], size=n_orders, p=[0.88, 0.09, 0.025, 0.005])
    rows = []
    for i in range(n_orders):
        for k in range(n_items[i]):
            c = int(rng.choice(len(cat_pt), p=cw[int(month_idx[i])]))
            ix = prod_by_cat[c]
            pj = int(rng.choice(ix, p=prod_w[c]))
            rows.append((i, k + 1, pj))
    it = pd.DataFrame(rows, columns=["oi", "order_item_id", "pj"])
    it["price"] = (base_price[it.pj] * rng.uniform(0.92, 1.08, len(it))).round(2)
    it["seller_j"] = p_seller[it.pj]
    cust_state_o = customers["customer_state"].values
    reg = lambda s: STATES[s][0]
    same_state = (s_state[it.seller_j] == cust_state_o[it.oi])
    same_reg = np.array([reg(a) == reg(b) for a, b in zip(s_state[it.seller_j], cust_state_o[it.oi])])
    base_fr = np.where(same_state, 8.0, np.where(same_reg, 14.0, 23.0))
    it["freight_value"] = (base_fr + weight[it.pj] / 1000 * 2.2 + 0 * rng.random(len(it))).round(2)
    it["freight_value"] = (it["freight_value"] * rng.uniform(0.85, 1.25, len(it))).round(2)

    # ---------------------------------------------------------------- order timeline
    status = rng.choice(["delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"],
                        size=n_orders, p=[0.965, 0.011, 0.006, 0.006, 0.004, 0.004, 0.002, 0.002])
    first = it.groupby("oi").first()
    fs = first["seller_j"].values
    exp_transit = np.where(s_state[fs] == cust_state_o, 2.5,
                           np.where([reg(a) == reg(b) for a, b in zip(s_state[fs], cust_state_o)], 5.0, 9.0))
    exp_transit = exp_transit + np.where(np.isin(cust_state_o, ["PA", "AM", "AC", "AP", "RR", "RO", "MA", "PI", "CE", "RN", "PB", "AL", "SE"]), 3.5, 0)
    crunch = np.where(month_idx == 10, 1.35, 1.0)
    handling = rng.gamma(2.0, s_handling[fs] / 2.0)
    transit = exp_transit * rng.lognormal(0, 0.38, n_orders) * s_delay_mult[fs] * crunch
    approved = purchase + pd.to_timedelta(rng.exponential(9, n_orders), "h")
    carrier = approved + pd.to_timedelta(handling, "D")
    delivered = carrier + pd.to_timedelta(transit, "D")
    estimated = (purchase + pd.to_timedelta(np.ceil(8.5 + 1.35 * exp_transit), "D")).normalize()
    orders = pd.DataFrame({"order_id": order_ids, "customer_id": cust_ids, "order_status": status,
                           "order_purchase_timestamp": purchase, "order_approved_at": approved,
                           "order_delivered_carrier_date": carrier, "order_delivered_customer_date": delivered,
                           "order_estimated_delivery_date": estimated})
    s = orders.order_status
    orders.loc[s.isin(["created"]), "order_approved_at"] = pd.NaT
    orders.loc[s.isin(["created", "approved", "invoiced", "processing", "unavailable", "canceled"]), "order_delivered_carrier_date"] = pd.NaT
    orders.loc[s != "delivered", "order_delivered_customer_date"] = pd.NaT
    bad = rng.choice(np.where(s == "delivered")[0], 15, replace=False)  # defect: delivered before purchase
    orders.loc[bad, "order_delivered_customer_date"] = orders.loc[bad, "order_purchase_timestamp"] - pd.Timedelta(days=2)

    # ---------------------------------------------------------------- payments
    tot = it.assign(v=it.price + it.freight_value).groupby("oi")["v"].sum().reindex(range(n_orders)).values
    pay_rows = []
    for i in range(n_orders):
        v = round(float(tot[i]), 2)
        inst_p = [0.5, 0.12, 0.1, 0.08, 0.05, 0.06, 0.02, 0.07] if v < 250 else [0.2, 0.1, 0.12, 0.1, 0.08, 0.15, 0.05, 0.2]
        inst = int(rng.choice([1, 2, 3, 4, 5, 6, 8, 10], p=inst_p))
        r = rng.random()
        if r < 0.74:
            pay_rows.append((order_ids[i], 1, "credit_card", inst, v))
        elif r < 0.935:
            pay_rows.append((order_ids[i], 1, "boleto", 1, v))
        elif r < 0.985:
            part = round(v * rng.uniform(0.2, 0.7), 2)
            pay_rows.append((order_ids[i], 1, "voucher", 1, part))
            pay_rows.append((order_ids[i], 2, "credit_card", inst, round(v - part, 2)))
        else:
            pay_rows.append((order_ids[i], 1, "debit_card", 1, v))
    payments = pd.DataFrame(pay_rows, columns=["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"])

    # ---------------------------------------------------------------- reviews
    delay = (orders.order_delivered_customer_date.dt.normalize() - orders.order_estimated_delivery_date).dt.days.values
    late = np.nan_to_num(delay, nan=-1) > 0
    probs_ok = [0.04, 0.03, 0.08, 0.20, 0.65]
    probs_late = [0.40, 0.18, 0.16, 0.12, 0.14]
    probs_very_late = [0.62, 0.17, 0.10, 0.06, 0.05]
    probs_cancel = [0.7, 0.1, 0.1, 0.05, 0.05]
    rev_rows = []
    for i in range(n_orders):
        if rng.random() > 0.985 or status[i] in ("created", "approved"):
            continue
        p = probs_cancel if status[i] in ("canceled", "unavailable") else (probs_very_late if delay[i] > 5 else probs_late) if late[i] else probs_ok
        sc = int(rng.choice([1, 2, 3, 4, 5], p=p))
        msg = None
        if rng.random() < (0.55 if sc <= 2 else 0.3):
            pool_c = (COMMENTS_BAD_LATE if late[i] else COMMENTS_BAD_OTHER) if sc <= 2 else COMMENTS_MID if sc == 3 else COMMENTS_GOOD
            msg = str(rng.choice(pool_c))
        base_dt = orders.order_delivered_customer_date.iloc[i]
        if pd.isna(base_dt):
            base_dt = orders.order_estimated_delivery_date.iloc[i]
        created = (base_dt + pd.Timedelta(days=int(rng.integers(0, 3)))).normalize()
        rev_rows.append((f"{0xAB:04x}{int(rng.integers(0, 2**60)):015x}{i:013x}", order_ids[i], sc, None, msg, created,
                         created + pd.Timedelta(days=int(rng.integers(0, 4)), hours=int(rng.integers(0, 24)))))
    reviews = pd.DataFrame(rev_rows, columns=["review_id", "order_id", "review_score", "review_comment_title",
                                              "review_comment_message", "review_creation_date", "review_answer_timestamp"])
    reviews = pd.concat([reviews, reviews.sample(60, random_state=1)], ignore_index=True)  # defect: duplicate rows

    # ---------------------------------------------------------------- assemble item table & geo
    order_items = pd.DataFrame({
        "order_id": [order_ids[i] for i in it.oi], "order_item_id": it.order_item_id.values,
        "product_id": [p_ids[j] for j in it.pj], "seller_id": [s_ids[j] for j in it.seller_j],
        "shipping_limit_date": [purchase[i] + pd.Timedelta(days=3) for i in it.oi],
        "price": it.price.values, "freight_value": it.freight_value.values})
    geo = []
    for st, (_, lat, lon) in STATES.items():
        k = 60
        geo.append(pd.DataFrame({"geolocation_zip_code_prefix": rng.integers(1000, 99999, k),
                                 "geolocation_lat": lat + rng.normal(0, 0.8, k), "geolocation_lng": lon + rng.normal(0, 0.8, k),
                                 "geolocation_city": [f"{st.lower()}_city_{j % 8}" for j in range(k)], "geolocation_state": st}))
    geolocation = pd.concat(geo, ignore_index=True)
    translation = pd.DataFrame({"product_category_name": cat_pt, "product_category_name_english": [CATEGORIES[c][0] for c in cat_pt]})

    tables = {"customers": customers, "orders": orders, "order_items": order_items, "payments": payments,
              "reviews": reviews, "products": products, "sellers": sellers, "geolocation": geolocation,
              "category_translation": translation}
    for name, df in tables.items():
        df.to_csv(out_dir / OLIST_FILES[name], index=False)
    (out_dir / ".synthetic").write_text("synthetic data generated by python/generate_sample_data.py")
    return tables


if __name__ == "__main__":
    tabs = generate()
    for k, v in tabs.items():
        print(f"{k:22s} {len(v):>8,d} rows")
