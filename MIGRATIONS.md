# Database Migrations

## cec5ebc

Remove the `searchindex` table and add a product column instead.

    ALTER TABLE products ADD COLUMN title_norm character varying(120);
    UPDATE products SET title_norm = searchindex.title_norm
        FROM searchindex WHERE id = searchindex.prod_id;
    ALTER TABLE products ALTER COLUMN title_norm SET NOT NULL;
    DROP TABLE searchindex;

## a2c8a1a

Add deleted columns to files and downloads. Also run the `initialize-db`
script to create the `changerecords` table.

    ALTER TABLE files ADD COLUMN deleted BOOLEAN;
    ALTER TABLE downloads ADD COLUMN deleted BOOLEAN;
    UPDATE files SET deleted=FALSE;
    UPDATE downloads SET deleted=FALSE;
    ALTER TABLE files ALTER COLUMN deleted SET NOT NULL;
    ALTER TABLE downloads ALTER COLUMN deleted SET NOT NULL;

## fbfe39c

Make almost all columns optional to allow unavailable games to be added.

    ALTER TABLE products ADD COLUMN store_date DATE;
    ALTER TABLE products ADD COLUMN availability SMALLINT;

    ALTER TABLE products ALTER COLUMN title DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN slug DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN forum_id DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN product_type DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN is_secret DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN is_price_visible DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN can_be_reviewed DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN cs_windows DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN cs_mac DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN cs_linux DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN os_windows DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN os_mac DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN os_linux DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN is_coming_soon DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN is_pre_order DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN development_active DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN rating DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN votes_count DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN reviews_count DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN developer_slug DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN publisher_slug DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN image_background DROP NOT NULL;
    ALTER TABLE products ALTER COLUMN image_logo DROP NOT NULL;

Make prices optional and delete invalid entries

    ALTER TABLE pricerecords ALTER COLUMN price_base DROP NOT NULL;
    ALTER TABLE pricerecords ALTER COLUMN price_final DROP NOT NULL;

    DELETE FROM pricerecords WHERE price_base = 99.99 AND price_final = 99.99;

## 86b9c8e

Clean up old content system changelog entries.

     DELETE FROM changerecords WHERE type_prim='product' AND type_sec='cs';

## 4c36b1c

Add download systems caching.

    ALTER TABLE products ADD COLUMN dl_windows BOOLEAN;
    ALTER TABLE products ADD COLUMN dl_mac BOOLEAN;
    ALTER TABLE products ADD COLUMN dl_linux BOOLEAN;

## 41f2860

Rename availability to access.

    ALTER TABLE products RENAME COLUMN availability TO access;
    UPDATE changerecords SET type_sec='access' WHERE type_sec='avail';
