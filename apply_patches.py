import re, textwrap

filepath = "app/routers/lovi.py"
with open(filepath, "r") as f:
    content = f.read()

# ========== 1. Добавляем import для fetch_overpass ==========
if "fetch_overpass" not in content:
    # Вставим функцию после последнего import (перед STRATEGY_DEFAULTS)
    imports_end = re.search(r'\n(STRATEGY_DEFAULTS)', content)
    if imports_end:
        insert_pos = imports_end.start()
        overpass_func = textwrap.dedent("""
        # ── Overpass API ─────────────────────────────────────────────────────
        OVERPASS_URL = "https://overpass-api.de/api/interpreter"

        async def fetch_overpass(lat: float, lon: float, radius: int, query_tags: list[str] | None = None) -> list[dict]:
            if query_tags is None:
                query_tags = ["amenity=massage", "shop=beauty", "shop=massage"]
            tags_filter = "|".join(f'["{t.split("=")[0]}"="{t.split("=")[1]}"]' for t in query_tags)
            query = f\"\"\"
            [out:json];
            (
              node{tags_filter}(around:{radius},{lat},{lon});
              way{tags_filter}(around:{radius},{lat},{lon});
              relation{tags_filter}(around:{radius},{lat},{lon});
            );
            out center;
            \"\"\"
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(OVERPASS_URL, data={"data": query})
                resp.raise_for_status()
                data = resp.json()
            items = []
            for el in data.get("elements", []):
                point = el.get("center", el) if el["type"] != "node" else el
                lat2 = point.get("lat")
                lon2 = point.get("lon")
                if lat2 is None or lon2 is None:
                    continue
                tags = el.get("tags", {})
                name = tags.get("name", "")
                items.append({
                    "source": "osm",
                    "name": name,
                    "address": (tags.get("addr:street", "") + " " + tags.get("addr:housenumber", "")).strip(),
                    "rating": None,
                    "reviews_count": 0,
                    "rubrics": [tags.get("amenity") or tags.get("shop") or "салон"],
                    "point": {"lat": lat2, "lon": lon2},
                    "dgis_id": f"osm-{el['type']}-{el['id']}"
                })
            return items
        """)
        content = content[:insert_pos] + overpass_func + "\n" + content[insert_pos:]
        print("✓ fetch_overpass добавлена")
    else:
        print("⚠ Не найдено место для вставки fetch_overpass")
else:
    print("✓ fetch_overpass уже есть")

# ========== 2. Обновляем ZONE_CONFIG (добавляем bbox) ==========
# Ищем конец словаря ZONE_CONFIG (закрывающая скобка после последней зоны)
zone_config_pattern = r'(ZONE_CONFIG\s*=\s*\{.*?\n\})'
match = re.search(zone_config_pattern, content, re.DOTALL)
if match:
    old_config = match.group(1)
    # Новый словарь с bbox (координаты приближены по описанию барьеров)
    new_config = """ZONE_CONFIG = {
    "yabloneviy-sad":            {"lat": 55.6455, "lon": 37.5185, "radius": 550, "bbox": (55.642, 37.513, 55.649, 37.526)},
    "konkovskie-prudy":          {"lat": 55.6370, "lon": 37.5155, "radius": 600, "bbox": (55.633, 37.510, 55.641, 37.521)},
    "derevlyovskiy-prud":        {"lat": 55.6505, "lon": 37.5490, "radius": 580, "bbox": (55.647, 37.543, 55.654, 37.555)},
    "belyaevo-center":           {"lat": 55.6468, "lon": 37.5360, "radius": 480, "bbox": (55.643, 37.530, 55.6505, 37.543)},
    "obrucheva-st":              {"lat": 55.6560, "lon": 37.5310, "radius": 560, "bbox": (55.652, 37.525, 55.660, 37.537)},
    "kaluzhskaya-border":        {"lat": 55.6635, "lon": 37.5145, "radius": 520, "bbox": (55.660, 37.509, 55.667, 37.520)},
    "rudn":                      {"lat": 55.6530, "lon": 37.5655, "radius": 600, "bbox": (55.649, 37.559, 55.657, 37.572)},
    "samorodinka":               {"lat": 55.6620, "lon": 37.5720, "radius": 580, "bbox": (55.658, 37.566, 55.666, 37.578)},
    "vorontsovskaya":            {"lat": 55.6680, "lon": 37.5350, "radius": 580, "bbox": (55.664, 37.529, 55.672, 37.541)},
    "novye-cheremushki":         {"lat": 55.6740, "lon": 37.5440, "radius": 560, "bbox": (55.670, 37.538, 55.678, 37.550)},
    "novatorskaya":              {"lat": 55.6760, "lon": 37.5210, "radius": 570, "bbox": (55.672, 37.515, 55.680, 37.527)},
    "cheremushki-north":         {"lat": 55.6650, "lon": 37.5580, "radius": 560, "bbox": (55.661, 37.552, 55.669, 37.564)},
    "cheremushki-center":        {"lat": 55.6720, "lon": 37.5600, "radius": 560, "bbox": (55.668, 37.554, 55.676, 37.566)},
    "cheremushki-south":         {"lat": 55.6790, "lon": 37.5620, "radius": 550, "bbox": (55.675, 37.556, 55.683, 37.568)},
    "lomonosovsky-vorontsovsky": {"lat": 55.6710, "lon": 37.5080, "radius": 580, "bbox": (55.667, 37.502, 55.675, 37.514)},
    "lomonosovsky-leninsky":     {"lat": 55.6820, "lon": 37.5010, "radius": 600, "bbox": (55.678, 37.495, 55.686, 37.507)},
    "lomonosovsky-nakhimovsky":  {"lat": 55.6790, "lon": 37.5170, "radius": 560, "bbox": (55.675, 37.511, 55.683, 37.523)},
}"""
    content = content.replace(old_config, new_config)
    print("✓ ZONE_CONFIG обновлён с bbox")
else:
    print("⚠ Не удалось найти ZONE_CONFIG для замены")

# ========== 3. Модифицируем refresh_zones: добавляем Overpass, bbox, предохранитель ==========
# Ищем блок внутри цикла for z in zones: где вызывается fetch_2gis и upsert
# Простейший способ: заменить тело функции refresh_zones полностью (от def до конца)
# Но чтобы не трогать другие функции, можно найти уникальные строки-маркеры.
# Заменим конкретные фрагменты: вызов fetch_2gis и блок с upsert.

# Ищем строчку "# Сохраняем в кэш (upsert)" и от неё до конца цикла меняем логику.
# Более безопасно: найти весь блок обработки зоны внутри цикла for z in zones: (строки с async def refresh_zones)
# Следующим патчем мы перепишем внутренности цикла.

# Маркер: строка "# Сохраняем в кэш (upsert)"
old_upsert_block = '            try:\n                supabase.table("zone_cache").upsert({\n                    "zone_id": zone_id,\n                    "count": count,\n                    "items": items,\n                    "fetched_at": now_iso,\n                }, on_conflict="zone_id").execute()\n            except Exception as e:\n                print(f"[ZONES] ошибка сохранения кэша для {zone_id}: {e}")'
new_upsert_block = '''            # Предохранитель: не записываем 0, если есть старые данные
            existing = supabase.table("zone_cache") \\
                .select("count") \\
                .eq("zone_id", zone_id) \\
                .maybe_single() \\
                .execute()
            should_update = True
            if count == 0 and existing.data and existing.data.get("count", 0) > 0:
                should_update = False
                print(f"[ZONES] Пропущено обновление {zone_id}: count=0 при старом >0")
            if should_update:
                try:
                    supabase.table("zone_cache").upsert({
                        "zone_id": zone_id,
                        "count": count,
                        "items": items,
                        "fetched_at": now_iso,
                    }, on_conflict="zone_id").execute()
                except Exception as e:
                    print(f"[ZONES] ошибка сохранения кэша для {zone_id}: {e}")'''

if old_upsert_block in content:
    content = content.replace(old_upsert_block, new_upsert_block)
    print("✓ Предохранитель добавлен в upsert")
else:
    print("⚠ Не удалось найти блок upsert для замены — возможно, код изменился.")

# Теперь вставим Overpass и объединение сразу после получения items от 2GIS
# Маркер: строка "items = []" и затем "# Сохраняем в кэш (upsert)"
# Вставим новый блок между получением items и проверкой/upsert
old_osm_placeholder = '                    count = len(items)\n            except Exception as e:\n                items = []\n                count = 0\n                print(f"[ZONES] ошибка для {zone_id}: {e}")'
new_osm_block = '''                    count = len(items)
            except Exception as e:
                items = []
                count = 0
                print(f"[ZONES] ошибка 2GIS для {zone_id}: {e}")
            # Дополнительный запрос Overpass
            try:
                osm_items = await fetch_overpass(lat, lon, radius)
            except Exception as e:
                osm_items = []
                print(f"[ZONES] ошибка Overpass для {zone_id}: {e}")
            # Объединение с дедупликацией (приоритет 2GIS)
            seen_coords = set()
            combined = []
            for it in items + osm_items:
                coord_key = f"{it['point']['lat']:.5f},{it['point']['lon']:.5f}"
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    combined.append(it)
            items = combined
            # Применяем bbox если задан
            bbox = z.get("bbox")
            if bbox:
                items = [it for it in items if bbox[0] <= it["point"]["lat"] <= bbox[2] and bbox[1] <= it["point"]["lon"] <= bbox[3]]
            count = len(items)'''

if old_osm_placeholder in content:
    content = content.replace(old_osm_placeholder, new_osm_block)
    print("✓ Overpass и bbox интегрированы")
else:
    print("⚠ Не удалось найти место для вставки Overpass — проверьте код")

# Сохраняем изменённый файл
with open(filepath, "w") as f:
    f.write(content)
print("\n✓ Все изменения успешно внесены в lovi.py")
