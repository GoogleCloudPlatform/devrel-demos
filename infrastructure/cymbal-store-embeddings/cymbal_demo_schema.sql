-- Copyright 2024 Google LLC.
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.2
-- Dumped by pg_dump version 15.4 (Debian 15.4-1.pgdg110+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cymbal_embedding; Type: TABLE; Schema: public; 
--

CREATE TABLE public.cymbal_embedding (
    uniq_id character varying(100),
    description text,
    embedding public.vector(768)
);

--
-- Name: cymbal_inventory; Type: TABLE; Schema: public; 
--

CREATE TABLE public.cymbal_inventory (
    store_id integer NOT NULL,
    uniq_id text NOT NULL,
    inventory integer NOT NULL
);

--
-- Name: cymbal_products; Type: TABLE; Schema: public; 
--

CREATE TABLE public.cymbal_products (
    uniq_id character varying(100),
    crawl_timestamp timestamp without time zone,
    product_url text,
    product_name text,
    product_description text,
    list_price numeric,
    sale_price numeric,
    brand text,
    item_number text,
    gtin text,
    package_size text,
    category text,
    postal_code text,
    available boolean
);

--
-- Name: cymbal_stores; Type: TABLE; Schema: public; 
--

CREATE TABLE public.cymbal_stores (
    store_id integer NOT NULL,
    name text,
    url text,
    street_address text,
    city text,
    state character varying(3),
    zip_code integer,
    country character varying(3),
    phone_number_1 text,
    phone_number_2 text,
    fax_1 text,
    fax_2 text,
    email_1 text,
    email_2 text,
    website text,
    open_hours text,
    latitude text,
    longitude text,
    facebook text,
    twitter text,
    instagram text,
    pinterest text,
    youtube text
);


--
-- Name: walmart_stores_store_id_seq; Type: SEQUENCE; Schema: public; 
--

CREATE SEQUENCE public.walmart_stores_store_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: walmart_stores_store_id_seq; Type: SEQUENCE OWNED BY; Schema: public; 
--

ALTER SEQUENCE public.walmart_stores_store_id_seq OWNED BY public.cymbal_stores.store_id;


--
-- Name: cymbal_stores store_id; Type: DEFAULT; Schema: public; 
--

ALTER TABLE ONLY public.cymbal_stores ALTER COLUMN store_id SET DEFAULT nextval('public.walmart_stores_store_id_seq'::regclass);


--
-- Name: cymbal_inventory walmart_inventory_pkey; Type: CONSTRAINT; Schema: public; 
--

ALTER TABLE ONLY public.cymbal_inventory
    ADD CONSTRAINT walmart_inventory_pkey PRIMARY KEY (store_id, uniq_id);


--
-- Name: cymbal_stores walmart_stores_pkey; Type: CONSTRAINT; Schema: public; 
--

ALTER TABLE ONLY public.cymbal_stores
    ADD CONSTRAINT walmart_stores_pkey PRIMARY KEY (store_id);


--
-- PostgreSQL database dump complete
--

