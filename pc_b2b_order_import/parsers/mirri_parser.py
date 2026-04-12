# -*- coding: utf-8 -*-
"""
Parser para ficheros CSV exportados desde la plataforma MIRRI.

Formato MIRRI:
- Fichero CSV con 23 columnas
- Cabeceras con corchetes en la primera y última columna:
  [designer id, color code, season code(CarryOver), category level 1,
   category level 2(Optional), category level 3, brand name,
   Size standard(Optional), size, skucode(Optional), retail price,
   supply price, stock, product name(Optional), color description(Optional),
   composition(Optional), made in(Optional), product description(Optional),
   size fit(Optional), images(Optional), Is Presale(Optional),
   Estimate Arrival time(Begin), Estimate Arrival time(End)]

- Separador: coma
- Encoding: latin-1 (contiene caracteres especiales)
- Esto es un catálogo/stock, NO un pedido de compra
- 15.000+ filas típicamente
- Los campos opcionales suelen estar vacíos en muchas filas
- El designer_id actúa como referencia del estilo
- Cada fila es un SKU único (designer_id + color_code + size)

Particularidades:
- Las cabeceras tienen espacios iniciales (excepto la primera)
- La primera cabecera tiene "[" y la última "]"
- Los precios usan punto decimal
- El stock es un entero
- Muchos campos opcionales (product name, composition, etc.) vacíos
"""
import csv
import logging
from io import StringIO

_logger = logging.getLogger(__name__)

# Mapeo de índices de columnas basado en el formato real observado
MIRRI_COLUMNS = {
    'designer_id': 0,
    'color_code': 1,
    'season_code': 2,
    'category_level_1': 3,
    'category_level_2': 4,
    'category_level_3': 5,
    'brand_name': 6,
    'size_standard': 7,
    'size': 8,
    'skucode': 9,
    'retail_price': 10,
    'supply_price': 11,
    'stock': 12,
    'product_name': 13,
    'color_description': 14,
    'composition': 15,
    'made_in': 16,
    'product_description': 17,
    'size_fit': 18,
    'images': 19,
    'is_presale': 20,
    'arrival_time_begin': 21,
    'arrival_time_end': 22,
}


def parse_mirri_file(file_content):
    """
    Parsea un fichero MIRRI (.csv) y retorna un diccionario con los productos
    y su stock.

    :param file_content: bytes del fichero CSV
    :return: dict con claves:
        - 'brands': set de marcas encontradas
        - 'products': list of dict (productos individuales por SKU)
        - 'total_rows': int
        - 'total_stock': float
    """
    # Intentar decodificar con varios encodings
    text_content = None
    for encoding in ('utf-8', 'latin-1', 'cp1252', 'iso-8859-1'):
        try:
            text_content = file_content.decode(encoding)
            break
        except (UnicodeDecodeError, AttributeError):
            continue

    if text_content is None:
        raise ValueError(
            "No se ha podido decodificar el fichero CSV. "
            "Probados: utf-8, latin-1, cp1252, iso-8859-1."
        )

    reader = csv.reader(StringIO(text_content))

    # Leer cabeceras y limpiar
    raw_headers = next(reader)
    headers = _clean_headers(raw_headers)

    _logger.info("MIRRI Parser: %d columnas detectadas: %s", len(headers), headers)

    # Construir mapeo dinámico de columnas por nombre
    # Usamos coincidencia exacta con los nombres de cabecera limpiados
    _HEADER_TO_KEY = {
        'designer id': 'designer_id',
        'color code': 'color_code',
        'season code': 'season_code',
        'category level 1': 'category_level_1',
        'category level 2': 'category_level_2',
        'category level 3': 'category_level_3',
        'brand name': 'brand_name',
        'size standard': 'size_standard',
        'size': 'size',
        'skucode': 'skucode',
        'retail price': 'retail_price',
        'supply price': 'supply_price',
        'stock': 'stock',
        'product name': 'product_name',
        'color description': 'color_description',
        'composition': 'composition',
        'made in': 'made_in',
        'product description': 'product_description',
        'size fit': 'size_fit',
        'images': 'images',
        'is presale': 'is_presale',
        'estimate arrival time': 'arrival_time_begin',
    }

    col_map = {}
    arrival_time_count = 0
    for idx, header in enumerate(headers):
        header_lower = header.lower().strip()
        if header_lower in _HEADER_TO_KEY:
            key = _HEADER_TO_KEY[header_lower]
            # Manejar las dos columnas "Estimate Arrival time"
            if header_lower == 'estimate arrival time':
                arrival_time_count += 1
                if arrival_time_count == 1:
                    col_map['arrival_time_begin'] = idx
                else:
                    col_map['arrival_time_end'] = idx
            else:
                col_map[key] = idx

    # Si no se detectaron bien las cabeceras, usar los índices por defecto
    if len(col_map) < 5:
        _logger.warning(
            "MIRRI Parser: Solo %d columnas mapeadas por nombre. "
            "Usando índices por defecto.",
            len(col_map),
        )
        col_map = MIRRI_COLUMNS.copy()

    result = {
        'brands': set(),
        'products': [],
        'total_rows': 0,
        'total_stock': 0.0,
    }

    line_num = 0
    for row in reader:
        if not row or len(row) < 13:
            continue

        line_num += 1
        designer_id = _safe_get(row, col_map.get('designer_id', 0))
        if not designer_id:
            continue

        color_code = _safe_get(row, col_map.get('color_code', 1))
        season_code = _safe_get(row, col_map.get('season_code', 2))
        cat_level_1 = _safe_get(row, col_map.get('category_level_1', 3))
        cat_level_2 = _safe_get(row, col_map.get('category_level_2', 4))
        cat_level_3 = _safe_get(row, col_map.get('category_level_3', 5))
        brand_name = _safe_get(row, col_map.get('brand_name', 6))
        size_standard = _safe_get(row, col_map.get('size_standard', 7))
        size = _safe_get(row, col_map.get('size', 8))
        skucode = _safe_get(row, col_map.get('skucode', 9))
        retail_price = _safe_float(_safe_get(row, col_map.get('retail_price', 10)))
        supply_price = _safe_float(_safe_get(row, col_map.get('supply_price', 11)))
        stock = _safe_float(_safe_get(row, col_map.get('stock', 12)))
        product_name = _safe_get(row, col_map.get('product_name', 13))
        color_description = _safe_get(row, col_map.get('color_description', 14))
        composition = _safe_get(row, col_map.get('composition', 15))
        made_in = _safe_get(row, col_map.get('made_in', 16))
        product_description = _safe_get(row, col_map.get('product_description', 17))
        size_fit = _safe_get(row, col_map.get('size_fit', 18))
        images = _safe_get(row, col_map.get('images', 19))
        is_presale = _safe_get(row, col_map.get('is_presale', 20))
        arrival_begin = _safe_get(row, col_map.get('arrival_time_begin', 21))
        arrival_end = _safe_get(row, col_map.get('arrival_time_end', 22))

        if brand_name:
            result['brands'].add(brand_name.strip())

        result['total_stock'] += stock
        result['products'].append({
            'line_number': line_num,
            'designer_id': designer_id.strip(),
            'color_code': color_code.strip() if color_code else '',
            'season_code': season_code.strip() if season_code else '',
            'category_level_1': cat_level_1.strip() if cat_level_1 else '',
            'category_level_2': cat_level_2.strip() if cat_level_2 else '',
            'category_level_3': cat_level_3.strip() if cat_level_3 else '',
            'brand_name': brand_name.strip() if brand_name else '',
            'size_standard': size_standard.strip() if size_standard else '',
            'size': size.strip() if size else '',
            'skucode': skucode.strip() if skucode else '',
            'retail_price': retail_price,
            'supply_price': supply_price,
            'stock': stock,
            'product_name': product_name.strip() if product_name else '',
            'color_description': color_description.strip() if color_description else '',
            'composition': composition.strip() if composition else '',
            'made_in': made_in.strip() if made_in else '',
            'product_description': product_description.strip() if product_description else '',
            'size_fit': size_fit.strip() if size_fit else '',
            'images': images.strip() if images else '',
            'is_presale': is_presale.strip() if is_presale else '',
            'arrival_time_begin': arrival_begin.strip() if arrival_begin else '',
            'arrival_time_end': arrival_end.strip() if arrival_end else '',
        })

    result['total_rows'] = line_num
    result['brands'] = list(result['brands'])

    _logger.info(
        "MIRRI Parser: %d filas, %d marcas, stock total=%.0f",
        result['total_rows'],
        len(result['brands']),
        result['total_stock'],
    )

    return result


def _clean_headers(raw_headers):
    """
    Limpia las cabeceras del CSV MIRRI.
    - Elimina corchetes [ y ]
    - Elimina espacios iniciales
    - Elimina sufijos como (Optional) y (CarryOver)
    """
    cleaned = []
    for h in raw_headers:
        h = h.strip()
        h = h.lstrip('[').rstrip(']')
        h = h.strip()
        # Eliminar sufijos entre paréntesis
        if '(' in h:
            h = h[:h.index('(')].strip()
        cleaned.append(h)
    return cleaned


def _safe_get(row, idx):
    """Obtiene un valor de la fila de forma segura."""
    if idx is None or idx >= len(row):
        return ''
    return row[idx] if row[idx] else ''


def _safe_float(value):
    """Convierte un valor a float de forma segura."""
    if not value:
        return 0.0
    try:
        return float(str(value).replace(',', '.').strip())
    except (ValueError, TypeError):
        return 0.0
