import math



def calc_pageinfo(page, num_products, items_per_page):
    num_pages = int(math.ceil(num_products / items_per_page))
    page = min(max(page, 1), num_pages)
    offset = (page - 1) * items_per_page
    page_info = {
        "is_first": page == 1,
        "is_last": page == num_pages,
        "page": page,
        "num_pages": num_pages,
        "from": offset,
        "to": offset + items_per_page,
        "prev_link": "", # Filled in later
        "next_link": ""
    }
    return page_info
