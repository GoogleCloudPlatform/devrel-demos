--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4
-- Dumped by pg_dump version 15.6 (Debian 15.6-0+deb12u1)

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

--
-- Name: google_columnar_engine; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS google_columnar_engine WITH SCHEMA public;


--
-- Name: google_db_advisor; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS google_db_advisor WITH SCHEMA public;


--
-- Name: google_ml_integration; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS google_ml_integration WITH SCHEMA public;


--
-- Name: EXTENSION google_ml_integration; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION google_ml_integration IS 'Google extension for ML integration';


--
-- Name: hypopg; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS hypopg WITH SCHEMA public;


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivf access method';

--
-- User CYMBAL
--
create user cymbal with password 'StrongPassword';

grant all on database cymbal_store to cymbal;

GRANT ALL ON SCHEMA public TO cymbal;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cymbal_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cymbal_embeddings (
    uniq_id bigint NOT NULL,
    product_embedding public.vector(768)
);


ALTER TABLE public.cymbal_embeddings OWNER TO postgres;

--
-- Name: cymbal_products; Type: TABLE; Schema: public; Owner: cymbal
--

CREATE TABLE public.cymbal_products (
    uniq_id bigint NOT NULL,
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


ALTER TABLE public.cymbal_products OWNER TO cymbal;

--
-- Name: cymbal_products_uniq_id_seq1; Type: SEQUENCE; Schema: public; Owner: cymbal
--

ALTER TABLE public.cymbal_products ALTER COLUMN uniq_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cymbal_products_uniq_id_seq1
    START WITH 0
    INCREMENT BY 1
    MINVALUE 0
    NO MAXVALUE
    CACHE 20
);


--
-- Data for Name: cymbal_embeddings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cymbal_embeddings (uniq_id, product_embedding) FROM stdin;
\.


--
-- Data for Name: cymbal_products; Type: TABLE DATA; Schema: public; Owner: cymbal
--

COPY public.cymbal_products (uniq_id, crawl_timestamp, product_url, product_name, product_description, list_price, sale_price, brand, item_number, gtin, package_size, category, postal_code, available) FROM stdin;
0	\N	\N	Toy Car	Friction powered car with realistic engine sounds and headlights	20	15	Vroom	\N	\N	\N	Cars	\N	\N
1	\N	\N	Dollhouse	Three-story dollhouse with furniture and accessories	50	40	Dream Home	\N	\N	\N	Dolls	\N	\N
2	\N	\N	Building Blocks	Set of 100 colorful building blocks	25	20	Block City	\N	\N	\N	Construction	\N	\N
3	\N	\N	Play Kitchen	Fully equipped play kitchen with stove, oven, and refrigerator	60	50	Cook 'n Play	\N	\N	\N	Pretend Play	\N	\N
4	\N	\N	Stuffed Animal	Soft and cuddly teddy bear	18	15	Teddy & Friends	\N	\N	\N	Animals	\N	\N
5	\N	\N	Action Figure	Superhero action figure with movable joints	22	18	Hero Force	\N	\N	\N	Action Figures	\N	\N
6	\N	\N	Board Game	Classic board game for 2-4 players	28	22	Fun & Games	\N	\N	\N	Board Games	\N	\N
7	\N	\N	Puzzle	100-piece puzzle with a farm scene	15	12	Puzzle Time	\N	\N	\N	Puzzles	\N	\N
8	\N	\N	Art Supplies	Set of crayons, markers, and paper	20	16	Crayola	\N	\N	\N	Art	\N	\N
9	\N	\N	Craft Kit	Make-your-own slime kit	18	14	Slime Time	\N	\N	\N	Crafts	\N	\N
10	\N	\N	Musical Instrument	Toy piano with 25 keys	30	25	Musical Fun	\N	\N	\N	Music	\N	\N
11	\N	\N	Ride-On Toy	Push-car with a steering wheel and horn	40	32	Wheely	\N	\N	\N	Ride-On Toys	\N	\N
12	\N	\N	Toy Train	Electric train set with track and accessories	55	45	Railway Express	\N	\N	\N	Trains	\N	\N
13	\N	\N	Play Tent	Foldable play tent with a fun animal design	35	28	Animal Den	\N	\N	\N	Tents	\N	\N
14	\N	\N	Sandpit	Plastic sandpit with lid and cover	60	50	Sandbox Fun	\N	\N	\N	Outdoor Play	\N	\N
15	\N	\N	Water Table	Interactive water table with water pump and accessories	45	38	Splash & Play	\N	\N	\N	Outdoor Play	\N	\N
16	\N	\N	Scooter	Three-wheeled scooter with adjustable handlebars	50	40	Scoot & Ride	\N	\N	\N	Ride-On Toys	\N	\N
17	\N	\N	Tricycle	Tricycle with a basket and bell	60	48	Trike Time	\N	\N	\N	Ride-On Toys	\N	\N
18	\N	\N	Balance Bike	Two-wheeled balance bike without pedals	40	32	Glide & Ride	\N	\N	\N	Ride-On Toys	\N	\N
19	\N	\N	Doll	18-inch doll with removable clothing and accessories	45	36	Dream Girl	\N	\N	\N	Dolls	\N	\N
20	\N	\N	Teddy Bear	Large teddy bear with a soft and cuddly fur	32	26	Teddy Time	\N	\N	\N	Animals	\N	\N
21	\N	\N	Building Set	Magnetic building set with 50 pieces	30	24	Magna Build	\N	\N	\N	Construction	\N	\N
22	\N	\N	Art Kit	Complete art kit with paints, brushes, and canvas	35	28	Masterpiece	\N	\N	\N	Art	\N	\N
23	\N	\N	Slime Kit	Make-your-own slime kit with glitter and scents	20	16	Slimelicious	\N	\N	\N	Crafts	\N	\N
24	\N	\N	Musical Set	Toy drum, tambourine, and xylophone set	28	22	Musical Magic	\N	\N	\N	Music	\N	\N
25	\N	\N	Play Mat	Large play mat with a colorful animal print	40	32	Animal Adventure	\N	\N	\N	Play Mats	\N	\N
26	\N	\N	Sensory Bin	Sensory bin filled with rice, beans, and small toys	35	28	Sensory Play	\N	\N	\N	Sensory Play	\N	\N
27	\N	\N	Playdough	Non-toxic playdough in a variety of colors	18	15	Play-Doh	\N	\N	\N	Playdough	\N	\N
28	\N	\N	Finger Puppets	Set of finger puppets with different animal characters	15	12	Puppet Pals	\N	\N	\N	Puppets	\N	\N
29	\N	\N	Play Silks	Set of colorful play silks for imaginative play	25	20	Silk Magic	\N	\N	\N	Pretend Play	\N	\N
30	\N	\N	Stuffed Elephant	Plush elephant with a soft and cuddly body	20	16	Elephant Tales	\N	\N	\N	Animals	\N	\N
31	\N	\N	Farm Playset	Toy farm with barn, animals, and tractor	45	36	Farm Frenzy	\N	\N	\N	Playsets	\N	\N
32	\N	\N	Construction Playset	Toy construction site with bulldozer, excavator, and dump truck	50	40	Construction Zone	\N	\N	\N	Playsets	\N	\N
33	\N	\N	Doctor Playset	Toy doctor's kit with stethoscope, bandages, and syringe	40	32	Doctor's Orders	\N	\N	\N	Playsets	\N	\N
34	\N	\N	Kitchen Playset	Toy kitchen with stove, oven, and sink	45	36	Kitchen Craze	\N	\N	\N	Playsets	\N	\N
35	\N	\N	Superhero Playset	Toy superhero headquarters with action figures and vehicles	60	48	Superhero Central	\N	\N	\N	Playsets	\N	\N
36	\N	\N	Stuffed Giraffe Plush Toy	32-inch plush giraffe with ultra-soft fur, perfect for cuddling and imaginative play	20.99	14.99	Aurora	\N	\N	\N	Animals	\N	\N
37	\N	\N	Interactive Dinosaur	Realistic Tyrannosaurus Rex dinosaur with sound and motion sensors, roars and moves when touched	29.99	19.99	National Geographic	\N	\N	\N	Animals	\N	\N
38	\N	\N	Building Block Set	100 colorful blocks in various shapes and sizes, promoting fine motor skills and creativity	19.99	14.99	LEGO	\N	\N	\N	Building	\N	\N
39	\N	\N	Play Kitchen Set	Fully equipped play kitchen with realistic appliances, sink, and storage space, encouraging imaginative play	99.99	79.99	KidKraft	\N	\N	\N	Pretend Play	\N	\N
40	\N	\N	Art Easel with Paper Roll	Double-sided art easel with a paper roll, storage shelves, and non-toxic crayons, promoting creativity	49.99	39.99	Melissa & Doug	\N	\N	\N	Arts & Crafts	\N	\N
41	\N	\N	Interactive Dollhouse	Three-level dollhouse with working lights, sounds, and accessories, providing hours of imaginative play	59.99	49.99	Barbie	\N	\N	\N	Dolls	\N	\N
42	\N	\N	Ride-On Scooter	Adjustable and foldable scooter with three wheels, promoting physical activity and balance	29.99	19.99	Razor	\N	\N	\N	Outdoor Toys	\N	\N
43	\N	\N	Board Game for Toddlers	Colorful and interactive board game with simple rules, promoting counting, matching, and cooperation	14.99	9.99	Learning Resources	\N	\N	\N	Games	\N	\N
44	\N	\N	Bath Time Submarine	Wind-up submarine toy that floats and sprays water, making bath time fun and engaging	9.99	7.99	Playskool	\N	\N	\N	Bath Toys	\N	\N
45	\N	\N	Musical Instrument Set	Colorful set of drums, xylophone, and tambourine, encouraging musical exploration and rhythm	24.99	19.99	B. Toys	\N	\N	\N	Music	\N	\N
46	\N	\N	Activity Walker	Stable and adjustable walker with a variety of interactive toys, promoting gross motor skills and coordination	59.99	49.99	VTech	\N	\N	\N	Baby Gear	\N	\N
47	\N	\N	Stacking Ring Toy	Vibrant and stackable rings with different textures, developing fine motor skills and hand-eye coordination	16.99	12.99	Manhattan Toy	\N	\N	\N	Baby Toys	\N	\N
48	\N	\N	Pop-Up Tunnel	Foldable and portable tunnel with bright colors and patterns, encouraging imaginative play and physical activity	19.99	14.99	Playskool	\N	\N	\N	Outdoor Toys	\N	\N
49	\N	\N	Magnetic Building Blocks	Colorful and magnetic building blocks in various shapes, promoting creativity, spatial reasoning, and problem-solving	49.99	39.99	Magna-Tiles	\N	\N	\N	Building	\N	\N
50	\N	\N	Art Supply Kit	Complete set of crayons, markers, paint, and paper, fostering creativity and artistic expression	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
51	\N	\N	Remote Control Car	Off-road remote control car with rugged tires and bright headlights, providing excitement and adventure	29.99	24.99	Hot Wheels	\N	\N	\N	Outdoor Toys	\N	\N
52	\N	\N	Bubble Machine	Powerful bubble machine that creates a flurry of bubbles, promoting outdoor fun and laughter	14.99	9.99	Gazillion	\N	\N	\N	Outdoor Toys	\N	\N
53	\N	\N	Science Experiment Kit	Hands-on science kit with safe and engaging experiments, fostering curiosity and discovery	24.99	19.99	Thames & Kosmos	\N	\N	\N	Science & Nature	\N	\N
54	\N	\N	Playmat with Tummy Time Mirror	Soft and comfortable playmat with a tummy time mirror, promoting visual development and motor skills	29.99	24.99	Skip Hop	\N	\N	\N	Baby Toys	\N	\N
55	\N	\N	Water Table	Interactive water table with pumps, fountains, and boats, providing sensory play and water exploration	59.99	49.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
56	\N	\N	Pretend Play Kitchen Accessories	Realistic kitchen accessories including pots, pans, utensils, and food, encouraging imaginative play	19.99	14.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
57	\N	\N	Building Block Train Set	Colorful and durable building block train set with magnetic connections, promoting creativity and engineering skills	24.99	19.99	Mega Bloks	\N	\N	\N	Building	\N	\N
58	\N	\N	Musical Rainbow	Interactive rainbow-shaped instrument with lights and sounds, encouraging musical exploration and color recognition	19.99	14.99	Fisher-Price	\N	\N	\N	Music	\N	\N
59	\N	\N	Electronic Learning Tablet	Educational tablet with interactive games, puzzles, and activities, promoting cognitive development and language skills	49.99	39.99	LeapFrog	\N	\N	\N	Learning Toys	\N	\N
60	\N	\N	Interactive Pet Simulator	Realistic pet simulator with interactive features, sounds, and accessories, fostering empathy and animal care	49.99	39.99	FurReal	\N	\N	\N	Pretend Play	\N	\N
61	\N	\N	Craft Kit for Slime Making	Complete kit for making and customizing slime, promoting creativity and sensory play	19.99	14.99	Elmer's	\N	\N	\N	Arts & Crafts	\N	\N
62	\N	\N	Personalized Name Puzzle	Custom-made wooden puzzle with a child's name, fostering letter recognition and spelling	19.99	14.99	Melissa & Doug	\N	\N	\N	Learning Toys	\N	\N
63	\N	\N	Interactive Shape Sorter	Colorful shape sorter with blocks of different shapes and sizes, developing problem-solving and shape recognition	14.99	9.99	VTech	\N	\N	\N	Baby Toys	\N	\N
64	\N	\N	Magnetic Drawing Board	Mess-free magnetic drawing board with colorful magnetic pens, encouraging creativity and fine motor skills	19.99	14.99	Doodle Pro	\N	\N	\N	Arts & Crafts	\N	\N
65	\N	\N	Building Block Vehicle Set	Set of colorful and durable building blocks designed to create vehicles, promoting imagination and engineering skills	24.99	19.99	Mega Bloks	\N	\N	\N	Building	\N	\N
66	\N	\N	Musical Instrument Set for Kids	Assortment of musical instruments including a ukulele, tambourine, and kazoo, fostering musical exploration and creativity	29.99	24.99	Hape	\N	\N	\N	Music	\N	\N
67	\N	\N	Bath Time Water Slide	Bath toy with a slide, scoops, and floating animals, providing water fun and sensory exploration	24.99	19.99	Skip Hop	\N	\N	\N	Bath Toys	\N	\N
68	\N	\N	Kinetic Sand Castle Building Set	Moldable and reusable kinetic sand with castle molds and tools, encouraging imaginative play and sensory development	19.99	14.99	National Geographic	\N	\N	\N	Sensory Toys	\N	\N
69	\N	\N	Teddy Bear Plush	Soft and cuddly teddy bear, perfect for snuggling. Comes in a variety of colors.	19.99	14.99	Teddy Bear Co.	\N	\N	\N	Plush Toys	\N	\N
70	\N	\N	Building Blocks	Set of 100 colorful building blocks, perfect for creativity and imagination.	24.99	19.99	Block World	\N	\N	\N	Building Toys	\N	\N
71	\N	\N	Play Kitchen Set	Fully equipped play kitchen set with stove, oven, sink, and refrigerator. Comes with pretend food and accessories.	49.99	39.99	Toy Time	\N	\N	\N	Pretend Play	\N	\N
72	\N	\N	Doll House	Three-story doll house with furniture and accessories. Perfect for imaginative play.	69.99	59.99	Dream Home	\N	\N	\N	Doll Houses	\N	\N
73	\N	\N	Remote Control Car	High-speed remote control car with lights and sounds. Perfect for outdoor play.	34.99	29.99	Speed Racers	\N	\N	\N	Remote Control Toys	\N	\N
74	\N	\N	Science Experiment Kit	Hands-on science experiment kit with over 20 experiments. Perfect for curious kids.	29.99	24.99	Science Wiz	\N	\N	\N	Science Toys	\N	\N
75	\N	\N	Art Supplies Set	Complete set of art supplies including crayons, markers, paint, and paper. Perfect for budding artists.	14.99	11.99	Creative Kids	\N	\N	\N	Art Toys	\N	\N
76	\N	\N	Princess Castle Play Tent	Foldable princess castle play tent with lights and decorations. Perfect for imaginative play.	39.99	29.99	Dream Castle	\N	\N	\N	Play Tents	\N	\N
77	\N	\N	Paw Patrol Figure Set	Set of 6 Paw Patrol figures including Chase, Marshall, Skye, and more.	24.99	19.99	Paw Patrol	\N	\N	\N	Action Figures	\N	\N
78	\N	\N	Unicorn Figurine	Sparkling unicorn figurine with glitter and a flowing mane. Perfect for imaginative play.	12.99	9.99	Fantasy World	\N	\N	\N	Figurines	\N	\N
79	\N	\N	Board Game	Classic board game with dice, game board, and playing pieces. Perfect for family game night.	19.99	14.99	Game Time	\N	\N	\N	Board Games	\N	\N
80	\N	\N	Card Game	Fun card game with colorful cards and easy-to-follow instructions. Perfect for kids and adults.	9.99	7.99	Card Sharks	\N	\N	\N	Card Games	\N	\N
81	\N	\N	Puzzle	100-piece puzzle with a vibrant image. Perfect for problem-solving and creativity.	14.99	11.99	Puzzle Time	\N	\N	\N	Puzzles	\N	\N
82	\N	\N	Musical Instrument	Toy musical instrument with lights, sounds, and different modes. Perfect for introducing music to kids.	19.99	14.99	Little Musicians	\N	\N	\N	Musical Toys	\N	\N
83	\N	\N	Bath Toys	Set of 6 colorful bath toys that float and squirt water. Perfect for bath time fun.	12.99	9.99	Bath Time Buddies	\N	\N	\N	Bath Toys	\N	\N
84	\N	\N	Stuffed Animal	Cuddly stuffed animal with soft fur and embroidered details. Perfect for snuggling and play.	14.99	11.99	Stuffed Friends	\N	\N	\N	Plush Toys	\N	\N
85	\N	\N	Play Mat	Soft and comfortable play mat with a variety of colors and patterns. Perfect for tummy time and sensory play.	29.99	24.99	Baby Zone	\N	\N	\N	Play Mats	\N	\N
86	\N	\N	Learning Tablet	Interactive learning tablet with educational apps, games, and videos. Perfect for early learning.	49.99	39.99	Smart Kids	\N	\N	\N	Learning Toys	\N	\N
87	\N	\N	Ride-On Toy	Colorful ride-on toy with wheels and a steering wheel. Perfect for gross motor development.	39.99	29.99	Ride & Roll	\N	\N	\N	Ride-On Toys	\N	\N
88	\N	\N	Dolls	Set of 2 dolls with different outfits and accessories. Perfect for imaginative play.	24.99	19.99	Doll Time	\N	\N	\N	Dolls	\N	\N
89	\N	\N	Toy Train	Classic toy train with tracks, engine, and cars. Perfect for imaginative play and problem-solving.	39.99	29.99	Train Time	\N	\N	\N	Toy Trains	\N	\N
90	\N	\N	Nintendo Switch Lite	Handheld gaming console with a 5.5-inch touchscreen	199.99	179.99	Nintendo	\N	\N	\N	Gaming	\N	\N
91	\N	\N	Pretend Food Set	Set of realistic pretend food items including fruits, vegetables, and dishes. Perfect for imaginative play.	19.99	14.99	Kitchen Fun	\N	\N	\N	Pretend Play	\N	\N
92	\N	\N	Magnetic Tiles	Set of magnetic tiles in different shapes and colors. Perfect for creativity and engineering skills.	29.99	24.99	Build & Play	\N	\N	\N	Building Toys	\N	\N
93	\N	\N	Art Easel	Sturdy art easel with a chalkboard and magnetic whiteboard. Perfect for budding artists.	49.99	39.99	Art Studio	\N	\N	\N	Art Toys	\N	\N
94	\N	\N	Play Tent	Spacious play tent with a fun design. Perfect for imaginative play and indoor adventures.	24.99	19.99	Tent Time	\N	\N	\N	Play Tents	\N	\N
95	\N	\N	Remote Control Robot	Interactive remote control robot with lights, sounds, and different modes. Perfect for imaginative play.	39.99	29.99	Robot Zone	\N	\N	\N	Remote Control Toys	\N	\N
96	\N	\N	Slime Kit	Complete slime kit with different colors and scents. Perfect for creativity and sensory play.	14.99	11.99	Slime Time	\N	\N	\N	Slime Toys	\N	\N
97	\N	\N	Scooter	Colorful scooter with adjustable height and hand brakes. Perfect for outdoor play and exercise.	49.99	39.99	Scoot & Ride	\N	\N	\N	Ride-On Toys	\N	\N
98	\N	\N	Walkie Talkies	Set of 2 walkie talkies with a long range. Perfect for outdoor adventures and imaginative play.	29.99	24.99	Talk & Play	\N	\N	\N	Electronic Toys	\N	\N
99	\N	\N	Sandbox	Spacious sandbox with a lid. Perfect for outdoor play and sensory development.	49.99	39.99	Sand & Sun	\N	\N	\N	Outdoor Toys	\N	\N
100	\N	\N	Water Table	Interactive water table with a variety of water features. Perfect for outdoor play and sensory development.	59.99	49.99	Water World	\N	\N	\N	Outdoor Toys	\N	\N
101	\N	\N	Trampoline	Small trampoline with a safety net. Perfect for outdoor play and exercise.	99.99	79.99	Jump & Bounce	\N	\N	\N	Outdoor Toys	\N	\N
102	\N	\N	Swing Set	Sturdy swing set with 2 swings and a slide. Perfect for outdoor play and exercise.	149.99	119.99	Swing & Play	\N	\N	\N	Outdoor Toys	\N	\N
103	\N	\N	Playhouse	Spacious playhouse with a door, windows, and a slide. Perfect for imaginative play and outdoor adventures.	199.99	149.99	Dream Playhouse	\N	\N	\N	Outdoor Toys	\N	\N
104	\N	\N	Action Figure, 12-inch, Super Hero, with Lights and Sounds	Highly detailed action figure of your child's favorite super hero, with realistic sound effects and light-up features.	19.99	14.99	Adventure Toys	\N	\N	\N	Action Figures	\N	\N
105	\N	\N	Doll, 18-inch, My Little Pony, with Accessories	Soft and cuddly 18-inch doll of your child's favorite My Little Pony character, with removable clothing and accessories.	24.99	19.99	Dolls and Accessories	\N	\N	\N	Dolls	\N	\N
106	\N	\N	Building Blocks, 100-Piece Set, Classic Colors	Classic building blocks in a variety of colors, perfect for imaginative play and developing fine motor skills.	14.99	10.99	Building and Construction Toys	\N	\N	\N	Building Blocks	\N	\N
107	\N	\N	Play Kitchen, with Lights and Sounds	Realistic play kitchen with lights, sounds, and working appliances, for hours of imaginative play.	49.99	39.99	Pretend Play Toys	\N	\N	\N	Play Kitchens	\N	\N
108	\N	\N	Art Set, 50-Piece, with Paints, Markers, and Crayons	Complete art set with a variety of paints, markers, and crayons, to encourage creativity and artistic expression.	19.99	14.99	Arts and Crafts	\N	\N	\N	Art Sets	\N	\N
109	\N	\N	Stuffed Animal, 12-inch, Soft and Cuddly	Soft and cuddly stuffed animal, perfect for snuggling and bedtime.	14.99	10.99	Stuffed Animals	\N	\N	\N	Stuffed Animals	\N	\N
110	\N	\N	Board Game, Classic Family Game, for Ages 5+	Classic family board game that encourages strategy, problem-solving, and social interaction.	19.99	14.99	Board Games	\N	\N	\N	Board Games	\N	\N
111	\N	\N	Ride-On Toy, Pedal-Powered, with Basket	Fun and active ride-on toy with pedals and a basket, for outdoor adventures.	49.99	39.99	Ride-On Toys	\N	\N	\N	Ride-On Toys	\N	\N
112	\N	\N	Science Kit, 50-Experiment Set, with Instructions	Exciting science kit with 50 hands-on experiments, to foster curiosity and exploration.	24.99	19.99	Science and Discovery Toys	\N	\N	\N	Science Kits	\N	\N
113	\N	\N	Musical Instrument, Keyboard, with 37 Keys	Compact and lightweight keyboard with 37 keys, perfect for introducing children to music.	29.99	24.99	Musical Instruments	\N	\N	\N	Keyboards	\N	\N
114	\N	\N	Puzzle, 100-Piece, Animals of the World	Beautiful and challenging 100-piece puzzle featuring animals from around the world.	14.99	10.99	Puzzles	\N	\N	\N	Puzzles	\N	\N
115	\N	\N	Construction Set, 200-Piece, with Instructions	Large construction set with 200 pieces and easy-to-follow instructions, for hours of building and creativity.	29.99	24.99	Building and Construction Toys	\N	\N	\N	Construction Sets	\N	\N
116	\N	\N	Dress-Up Clothes, Princess Costume, with Accessories	Complete princess costume with dress, tiara, wand, and shoes, for imaginative play and dress-up fun.	29.99	24.99	Pretend Play Toys	\N	\N	\N	Dress-Up Clothes	\N	\N
117	\N	\N	Toy Car, Remote-Controlled, with Lights and Sounds	Fast and furious remote-controlled toy car with lights and sounds, for thrilling races and stunts.	24.99	19.99	Remote Control Toys	\N	\N	\N	Toy Cars	\N	\N
118	\N	\N	Stuffed Animal, 18-inch, Unicorn, with Rainbow Mane	Magical and cuddly stuffed unicorn with a rainbow mane and tail, perfect for bedtime stories and imaginative play.	24.99	19.99	Stuffed Animals	\N	\N	\N	Stuffed Animals	\N	\N
119	\N	\N	Building Blocks, 200-Piece Set, Magnetic	Innovative building blocks with magnets, allowing for endless possibilities and creative structures.	29.99	24.99	Building and Construction Toys	\N	\N	\N	Building Blocks	\N	\N
120	\N	\N	Play Tent, Pop-Up, with Tunnel	Spacious and colorful pop-up play tent with a tunnel, for indoor and outdoor adventures.	24.99	19.99	Pretend Play Toys	\N	\N	\N	Play Tents	\N	\N
121	\N	\N	Art Set, Washable, with Paints, Markers, and Paper	Washable art set with paints, markers, and paper, for mess-free creativity and artistic exploration.	14.99	10.99	Arts and Crafts	\N	\N	\N	Art Sets	\N	\N
122	\N	\N	Stuffed Animal, 12-inch, Dinosaur, with Plush Fur	Realistic and soft stuffed dinosaur with plush fur, perfect for imaginative play and bedtime cuddles.	19.99	14.99	Stuffed Animals	\N	\N	\N	Stuffed Animals	\N	\N
123	\N	\N	Building Blocks, 150-Piece Set, with Wheels	Building blocks with wheels, encouraging creativity, fine motor skills, and problem-solving.	19.99	14.99	Building and Construction Toys	\N	\N	\N	Building Blocks	\N	\N
124	\N	\N	Play Kitchen, Compact, with Accessories	Compact and portable play kitchen with accessories, for pretend play and cooking adventures.	29.99	24.99	Pretend Play Toys	\N	\N	\N	Play Kitchens	\N	\N
125	\N	\N	Doll, 12-inch, Superhero, with Cape and Mask	Empowering superhero doll with cape and mask, for imaginative play and storytelling.	19.99	14.99	Dolls and Accessories	\N	\N	\N	Dolls	\N	\N
126	\N	\N	Science Kit, Volcano Eruption Experiment	Exciting science kit that allows kids to create their own volcanic eruption, fostering curiosity and exploration.	14.99	10.99	Science and Discovery Toys	\N	\N	\N	Science Kits	\N	\N
127	\N	\N	Board Game, Cooperative, for Ages 4+	Cooperative board game that encourages teamwork, problem-solving, and social interaction.	19.99	14.99	Board Games	\N	\N	\N	Board Games	\N	\N
489	\N	\N	Doll	18-inch baby doll with soft body and vinyl head.	99.99	79.99	American Girl	\N	\N	\N	Dolls & Accessories	\N	\N
128	\N	\N	Ride-On Toy, Scooter, with Adjustable Height	Adjustable height scooter for active play and developing balance and coordination.	39.99	34.99	Ride-On Toys	\N	\N	\N	Scooters	\N	\N
129	\N	\N	Art Set, Scratch and Sketch, with Stencils	Creative scratch and sketch art set with stencils, encouraging fine motor skills and artistic expression.	14.99	10.99	Arts and Crafts	\N	\N	\N	Art Sets	\N	\N
130	\N	\N	Stuffed Animal, 10-inch, Teddy Bear, with Movable Joints	Classic and adorable teddy bear with movable joints, for cuddling and pretend play.	14.99	10.99	Stuffed Animals	\N	\N	\N	Stuffed Animals	\N	\N
131	\N	\N	Building Blocks, 100-Piece Set, with Storage Bag	Building blocks with a convenient storage bag, for easy cleanup and organization.	19.99	14.99	Building and Construction Toys	\N	\N	\N	Building Blocks	\N	\N
132	\N	\N	Play Tent, Castle, with Drawbridge	Spacious and imaginative castle-themed play tent with a drawbridge, for hours of pretend play and adventure.	39.99	34.99	Pretend Play Toys	\N	\N	\N	Play Tents	\N	\N
133	\N	\N	Musical Instrument, Drum Set, with 3 Drums and Cymbals	Compact drum set with 3 drums and cymbals, for introducing children to music and rhythm.	29.99	24.99	Musical Instruments	\N	\N	\N	Drum Sets	\N	\N
134	\N	\N	Board Game, Strategy, for Ages 6+	Challenging strategy board game that encourages critical thinking and problem-solving.	24.99	19.99	Board Games	\N	\N	\N	Board Games	\N	\N
135	\N	\N	Ride-On Toy, Tricycle, with Basket	Sturdy and colorful tricycle with a basket, perfect for outdoor adventures and developing coordination.	49.99	39.99	Ride-On Toys	\N	\N	\N	Tricycles	\N	\N
136	\N	\N	Art Set, Watercolor, with Paints and Brushes	Watercolor art set with paints and brushes, encouraging creativity and exploration of color mixing.	19.99	14.99	Arts and Crafts	\N	\N	\N	Art Sets	\N	\N
137	\N	\N	Stuffed Animal, 15-inch, Giraffe, with Long Neck	Tall and cuddly stuffed giraffe with a long neck, perfect for bedtime stories and imaginative play.	24.99	19.99	Stuffed Animals	\N	\N	\N	Stuffed Animals	\N	\N
138	\N	\N	Stuffed Animal Elephant	Soft and cuddly plush elephant with embroidered eyes and tusks	12.99	9.99	Plush Pals	\N	\N	\N	Stuffed Animals	\N	\N
139	\N	\N	Action Figure Superhero	Articulated action figure with interchangeable accessories and cape	9.99	7.99	Super Squad	\N	\N	\N	Action Figures	\N	\N
140	\N	\N	Board Game Candy Land	Classic board game with colorful candy-themed pieces and spinner	14.99	11.99	Sweet Tooth Games	\N	\N	\N	Board Games	\N	\N
141	\N	\N	Building Block Set Classic	Set of 100 colorful interlocking building blocks for creative play	19.99	14.99	Block Builder	\N	\N	\N	Building Blocks	\N	\N
142	\N	\N	Play Kitchen Set	Interactive play kitchen with realistic appliances, sink, and accessories	49.99	39.99	KidKraft	\N	\N	\N	Play Kitchens	\N	\N
143	\N	\N	Dollhouse Victorian	Elegant dollhouse with multiple rooms, furniture, and accessories	34.99	29.99	Dreamy Homes	\N	\N	\N	Dollhouses	\N	\N
144	\N	\N	Remote Control Car Race Car	High-speed remote control car with sleek design and working headlights	29.99	24.99	Nitro Racers	\N	\N	\N	Remote Control Vehicles	\N	\N
145	\N	\N	Art Set Crayons and Markers	Set of crayons, markers, and paper for drawing and coloring	14.99	11.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
146	\N	\N	Craft Kit Slime Making	Materials and instructions for making your own colorful and stretchy slime	12.99	9.99	Slime Studio	\N	\N	\N	Craft Kits	\N	\N
147	\N	\N	Science Kit Volcano Eruption	Interactive science kit with materials to create a simulated volcanic eruption	19.99	14.99	Science Explorers	\N	\N	\N	Science Kits	\N	\N
148	\N	\N	Puzzle Animal Kingdom	100-piece puzzle featuring a vibrant animal kingdom scene	14.99	11.99	Puzzle Masters	\N	\N	\N	Puzzles	\N	\N
149	\N	\N	Book Adventure Time	Exciting children's book with imaginative characters and adventures	9.99	7.99	Story Magic	\N	\N	\N	Books	\N	\N
150	\N	\N	DVD Cars	Animated movie featuring beloved race cars and their adventures	14.99	11.99	Pixar	\N	\N	\N	DVDs	\N	\N
151	\N	\N	Video Game Super Mario	Classic video game with iconic characters and thrilling levels	39.99	34.99	Nintendo	\N	\N	\N	Video Games	\N	\N
152	\N	\N	Teddy Bear Classic	Soft and cuddly teddy bear with a timeless design	19.99	14.99	Teddy Tails	\N	\N	\N	Stuffed Animals	\N	\N
153	\N	\N	Dress-Up Set Princess	Sparkling dress-up set with tiara, wand, and accessories	29.99	24.99	Dress-Up Dreams	\N	\N	\N	Dress-Up Sets	\N	\N
154	\N	\N	Tool Set Pretend Play	Set of realistic-looking tools for imaginative play	14.99	11.99	Tool Time	\N	\N	\N	Pretend Play	\N	\N
155	\N	\N	Musical Instrument Keyboard	Small-sized keyboard with 37 keys and multiple sound effects	24.99	19.99	Music Makers	\N	\N	\N	Musical Instruments	\N	\N
156	\N	\N	Bath Toy Boat Set	Set of colorful and floating bath toys shaped like boats	12.99	9.99	Bathtime Buddies	\N	\N	\N	Bath Toys	\N	\N
157	\N	\N	Construction Vehicle Excavator	Large-scale construction vehicle with movable arm and scoop	39.99	34.99	Mighty Machines	\N	\N	\N	Construction Vehicles	\N	\N
158	\N	\N	Play Tent Castle	Foldable play tent with a castle-like design and windows	29.99	24.99	Playtime Adventures	\N	\N	\N	Play Tents	\N	\N
159	\N	\N	Science Kit Chemistry Lab	Set of materials and instructions for conducting basic chemistry experiments	24.99	19.99	Science Zone	\N	\N	\N	Science Kits	\N	\N
160	\N	\N	Book Harry Potter	First book in the popular children's fantasy series	14.99	11.99	J.K. Rowling	\N	\N	\N	Books	\N	\N
161	\N	\N	DVD Frozen	Animated movie featuring beloved characters and a magical winter setting	19.99	14.99	Disney	\N	\N	\N	DVDs	\N	\N
162	\N	\N	Video Game Minecraft	Open-world video game where players can build, explore, and create	29.99	24.99	Mojang	\N	\N	\N	Video Games	\N	\N
163	\N	\N	Stuffed Animal Unicorn	Sparkly and whimsical stuffed unicorn with a flowing mane and tail	16.99	12.99	Plush Pals	\N	\N	\N	Stuffed Animals	\N	\N
164	\N	\N	Action Figure Hero	Muscular action figure with detailed armor and weapons	14.99	11.99	Hero Force	\N	\N	\N	Action Figures	\N	\N
165	\N	\N	Board Game Monopoly Junior	Kid-friendly version of the classic board game with shorter gameplay	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
166	\N	\N	Building Block Set Creative	Set of 250 colorful and shaped building blocks for imaginative play	24.99	19.99	Block Builder	\N	\N	\N	Building Blocks	\N	\N
167	\N	\N	Play Kitchen Set Modern	Contemporary play kitchen with sleek appliances, sink, and accessories	59.99	49.99	KidKraft	\N	\N	\N	Play Kitchens	\N	\N
168	\N	\N	Dollhouse Dream House	Spacious dollhouse with multiple levels, rooms, and furniture	44.99	39.99	Dreamy Homes	\N	\N	\N	Dollhouses	\N	\N
169	\N	\N	Remote Control Vehicle Monster Truck	Rugged remote control monster truck with oversized wheels and suspension	34.99	29.99	Nitro Racers	\N	\N	\N	Remote Control Vehicles	\N	\N
170	\N	\N	Art Set Paint and Brushes	Set of paint, brushes, and canvas for painting and creative expression	19.99	14.99	Art Central	\N	\N	\N	Art Supplies	\N	\N
171	\N	\N	Craft Kit Jewelry Making	Materials and instructions for making your own bracelets, necklaces, and earrings	16.99	12.99	Craft Creations	\N	\N	\N	Craft Kits	\N	\N
172	\N	\N	Science Kit Solar System	Interactive science kit with models and materials to learn about the planets	29.99	24.99	Science Explorers	\N	\N	\N	Science Kits	\N	\N
173	\N	\N	Puzzle Dinosaur World	100-piece puzzle featuring a prehistoric dinosaur world scene	16.99	12.99	Puzzle Masters	\N	\N	\N	Puzzles	\N	\N
174	\N	\N	Book The Very Hungry Caterpillar	Classic children's book about a hungry caterpillar's journey	9.99	7.99	Eric Carle	\N	\N	\N	Books	\N	\N
175	\N	\N	DVD Toy Story	Animated movie featuring beloved toys and their adventures	16.99	12.99	Pixar	\N	\N	\N	DVDs	\N	\N
176	\N	\N	Video Game Super Smash Bros.	Exciting video game where players battle as iconic Nintendo characters	44.99	39.99	Nintendo	\N	\N	\N	Video Games	\N	\N
177	\N	\N	Action Figure, Superhero, 7-inch, with Accessories	Detailed figure with realistic details and accessories, perfect for imaginative play.	10.99	8.99	Superhero Toys	\N	\N	\N	Action Figures	\N	\N
178	\N	\N	Board Game, Strategy, for 2-4 Players	Classic strategy board game with easy-to-learn rules and engaging gameplay.	14.99	11.99	Board Games	\N	\N	\N	Strategy Games	\N	\N
179	\N	\N	Building Blocks, Creative, 100-Piece Set	Colorful and durable building blocks for creative construction and imaginative play.	19.99	15.99	Building Toys	\N	\N	\N	Creative Toys	\N	\N
180	\N	\N	Construction Vehicle, Dump Truck, with Lights and Sounds	Realistic dump truck with lights, sounds, and movable parts.	24.99	19.99	Construction Toys	\N	\N	\N	Vehicles	\N	\N
181	\N	\N	Craft Kit, Jewelry Making, for Girls	Complete kit with beads, wire, and instructions for making unique jewelry pieces.	16.99	13.99	Craft Kits	\N	\N	\N	Jewelry Making	\N	\N
182	\N	\N	Doll, Fashion, with Accessories	Stylish doll with fashionable clothing and accessories for imaginative play.	29.99	23.99	Dolls	\N	\N	\N	Fashion Dolls	\N	\N
183	\N	\N	Educational Toy, Science Experiment Kit	Hands-on kit with experiments that teach scientific concepts in a fun and engaging way.	24.99	19.99	Educational Toys	\N	\N	\N	Science Toys	\N	\N
184	\N	\N	Electronic Pet, Interactive, with Virtual Care	Virtual pet with interactive features and realistic responses for nurturing and caring play.	39.99	31.99	Electronic Toys	\N	\N	\N	Virtual Pets	\N	\N
185	\N	\N	Game Console, Portable, with Built-in Games	Compact and portable game console with a variety of built-in games for on-the-go entertainment.	99.99	79.99	Game Consoles	\N	\N	\N	Portable Consoles	\N	\N
186	\N	\N	Musical Instrument, Toy Guitar, for Kids	Colorful and easy-to-play guitar for introducing kids to music and creativity.	19.99	15.99	Musical Toys	\N	\N	\N	Toy Instruments	\N	\N
187	\N	\N	Puzzle, Jigsaw, 100-Piece, Animals	Challenging and educational jigsaw puzzle featuring colorful animal designs.	14.99	11.99	Puzzles	\N	\N	\N	Jigsaw Puzzles	\N	\N
188	\N	\N	Ride-On Toy, Electric Scooter, for Kids	Electric scooter with adjustable speed and safety features for outdoor play and adventure.	199.99	159.99	Ride-On Toys	\N	\N	\N	Electric Scooters	\N	\N
189	\N	\N	Science Experiment Kit, Chemistry Lab	Comprehensive kit with experiments and materials for exploring chemistry concepts.	39.99	31.99	Educational Toys	\N	\N	\N	Science Toys	\N	\N
190	\N	\N	Sports Equipment, Basketball Hoop, Adjustable	Adjustable basketball hoop with sturdy base and durable net for indoor or outdoor play.	49.99	39.99	Sports Equipment	\N	\N	\N	Basketball Hoops	\N	\N
191	\N	\N	Stuffed Animal, Teddy Bear, Extra Large	Soft and cuddly teddy bear, perfect for hugging and comforting.	29.99	23.99	Stuffed Animals	\N	\N	\N	Teddy Bears	\N	\N
192	\N	\N	Tabletop Game, Adventure, for 3-6 Players	Collaborative adventure game with immersive storytelling and engaging gameplay.	34.99	27.99	Tabletop Games	\N	\N	\N	Adventure Games	\N	\N
193	\N	\N	Toy Car, Race Car, with Remote Control	Fast and responsive race car with remote control for thrilling races and stunts.	29.99	23.99	Toy Cars	\N	\N	\N	Remote Control Cars	\N	\N
194	\N	\N	Toy Dollhouse, Wooden, with Furniture	Sturdy and detailed wooden dollhouse with furniture and accessories for imaginative play.	59.99	49.99	Dolls	\N	\N	\N	Dollhouses	\N	\N
195	\N	\N	Toy Kitchen, Playset, with Appliances	Realistic playset with appliances, cookware, and food accessories for pretend cooking and baking.	79.99	63.99	Play Kitchens	\N	\N	\N	Toy Kitchens	\N	\N
196	\N	\N	Toy Train Set, Electric, with Tracks and Train Cars	Electric train set with tracks, train cars, and accessories for hours of imaginative play.	99.99	79.99	Toy Trains	\N	\N	\N	Electric Trains	\N	\N
197	\N	\N	Video Game, Adventure, for Nintendo Switch	Epic adventure video game with stunning graphics and engaging gameplay.	59.99	49.99	Video Games	\N	\N	\N	Nintendo Switch Games	\N	\N
198	\N	\N	Board Game, Educational, for Ages 5-9	Interactive board game that teaches math, science, or language skills in a fun way.	19.99	15.99	Board Games	\N	\N	\N	Educational Games	\N	\N
199	\N	\N	Building Blocks, Magnetic, with 100 Pieces	Colorful magnetic blocks for building structures, shapes, and designs.	24.99	19.99	Building Toys	\N	\N	\N	Magnetic Blocks	\N	\N
200	\N	\N	Collectible Figurine, Superhero, Limited Edition	Limited edition figurine of a popular superhero character, perfect for collectors and fans.	49.99	39.99	Collectibles	\N	\N	\N	Superhero Figurines	\N	\N
201	\N	\N	Craft Kit, Slime Making, for Kids	Slime-making kit with ingredients, tools, and instructions for creating colorful and stretchy slime.	14.99	11.99	Craft Kits	\N	\N	\N	Slime Making	\N	\N
202	\N	\N	Doll, Baby, with Accessories	Realistic baby doll with accessories like bottles, diapers, and clothing for nurturing play.	29.99	23.99	Dolls	\N	\N	\N	Baby Dolls	\N	\N
203	\N	\N	Educational Toy, Coding Robot	Interactive robot that teaches basic coding concepts through play and exploration.	49.99	39.99	Educational Toys	\N	\N	\N	Coding Toys	\N	\N
204	\N	\N	Electronic Toy, Drone, with Camera	Compact and easy-to-fly drone with a built-in camera for aerial photography and videography.	79.99	63.99	Electronic Toys	\N	\N	\N	Drones	\N	\N
205	\N	\N	Game Console, Retro, with Classic Games	Retro game console with a collection of classic games for nostalgic entertainment.	49.99	39.99	Game Consoles	\N	\N	\N	Retro Consoles	\N	\N
206	\N	\N	Musical Instrument, Toy Piano, with 25 Keys	Compact toy piano with 25 keys for introducing kids to music and melodies.	24.99	19.99	Musical Toys	\N	\N	\N	Toy Pianos	\N	\N
207	\N	\N	Puzzle, 3D, World Globe	Educational puzzle that builds a 3D model of the world globe, teaching geography and countries.	34.99	27.99	Puzzles	\N	\N	\N	3D Puzzles	\N	\N
208	\N	\N	Ride-On Toy, Tricycle, with Basket	Sturdy and colorful tricycle with a basket for storage and transportation.	69.99	55.99	Ride-On Toys	\N	\N	\N	Tricycles	\N	\N
209	\N	\N	Crib	Sturdy crib with adjustable mattress height	150.00	120.00	DaVinci	\N	\N	\N	Cribs	\N	\N
490	\N	\N	Action Figure	Superhero action figure with accessories.	19.99	14.99	Marvel	\N	\N	\N	Action Figures	\N	\N
210	\N	\N	Science Experiment Kit, Volcano Making	Hands-on kit with materials to create a real erupting volcano, teaching about science and geology.	29.99	23.99	Educational Toys	\N	\N	\N	Science Toys	\N	\N
211	\N	\N	Sports Equipment, Soccer Ball, Regulation Size	Official regulation size soccer ball for playing and practicing the sport.	24.99	19.99	Sports Equipment	\N	\N	\N	Soccer Balls	\N	\N
212	\N	\N	Stuffed Animal, Unicorn, Plush	Soft and cuddly unicorn plush toy for imaginative play and comfort.	29.99	23.99	Stuffed Animals	\N	\N	\N	Unicorns	\N	\N
213	\N	\N	Tabletop Game, Strategy, for 2 Players	Two-player strategy game that requires critical thinking and planning.	34.99	27.99	Tabletop Games	\N	\N	\N	Strategy Games	\N	\N
214	\N	\N	Toy Car, Construction Truck, with Moving Parts	Realistic construction truck with moving parts and accessories for pretend play.	39.99	31.99	Toy Cars	\N	\N	\N	Construction Trucks	\N	\N
215	\N	\N	Action Figure	Articulated action figure of a popular superhero, with multiple points of movement and accessories	19.99	14.99	Superhero Corp	\N	\N	\N	Action Figures	\N	\N
216	\N	\N	Board Game	Classic board game for 2-4 players, involving strategy and luck	14.99	9.99	Game Masters	\N	\N	\N	Board Games	\N	\N
217	\N	\N	Building Blocks	Set of colorful building blocks in various shapes and sizes, for imaginative play	19.99	14.99	Block Builders	\N	\N	\N	Building Blocks	\N	\N
218	\N	\N	Card Game	Educational card game that teaches basic math or science concepts	9.99	6.99	Clever Kids	\N	\N	\N	Card Games	\N	\N
219	\N	\N	Collectible Doll	Fashion doll with stylish outfit and accessories, from a popular movie or TV show	19.99	14.99	Dream Dolls	\N	\N	\N	Dolls	\N	\N
220	\N	\N	Construction Set	Building set with bricks, beams, and gears, for creating structures and machines	24.99	19.99	Tech Builders	\N	\N	\N	Construction Sets	\N	\N
221	\N	\N	Craft Kit	Arts and crafts kit with materials and instructions for creating a specific project, like painting or sculpting	14.99	9.99	Creative Minds	\N	\N	\N	Craft Kits	\N	\N
222	\N	\N	Electronic Pet	Virtual pet with interactive features, like feeding, playing, and grooming	19.99	14.99	Cyber Pets	\N	\N	\N	Electronic Pets	\N	\N
223	\N	\N	Figure	Detailed and realistic figure of a popular character from a movie, TV show, or video game	14.99	9.99	Character Corp	\N	\N	\N	Figures	\N	\N
224	\N	\N	Game Console	Handheld game console with a variety of built-in games	79.99	59.99	Game Zone	\N	\N	\N	Game Consoles	\N	\N
225	\N	\N	Glow Stick	Assortment of glow sticks in different colors, for nighttime fun and safety	9.99	6.99	Party Central	\N	\N	\N	Glow Sticks	\N	\N
226	\N	\N	Kite	Large kite with colorful design and easy-to-fly features	19.99	14.99	Kite Masters	\N	\N	\N	Kites	\N	\N
227	\N	\N	Light-Up Toy	Light-up toy shaped like a popular character or animal, with flashing lights and sounds	14.99	9.99	Light Up Toys	\N	\N	\N	Light-Up Toys	\N	\N
228	\N	\N	Musical Instrument	Toy musical instrument, like a guitar, keyboard, or drum set	19.99	14.99	Music Makers	\N	\N	\N	Musical Instruments	\N	\N
229	\N	\N	Nerf Gun	Toy gun that shoots foam darts, for outdoor play and target practice	19.99	14.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
230	\N	\N	Painting Set	Set of paints, brushes, and a canvas for young artists to create their own masterpieces	14.99	9.99	Art Studio	\N	\N	\N	Painting Sets	\N	\N
231	\N	\N	Play Dough	Container of colorful play dough, for molding, sculpting, and imaginative play	9.99	6.99	Play Dough	\N	\N	\N	Play Dough	\N	\N
232	\N	\N	Plushie	Soft and cuddly stuffed animal shaped like a popular character or animal	19.99	14.99	Cuddle Buddies	\N	\N	\N	Plush Toys	\N	\N
233	\N	\N	Puzzle	Challenging puzzle with intricate design or picture, for developing problem-solving skills	14.99	9.99	Puzzle Masters	\N	\N	\N	Puzzles	\N	\N
234	\N	\N	Radio-Controlled Car	Radio-controlled car with various speeds and functions, for outdoor racing and stunts	29.99	24.99	RC Cars	\N	\N	\N	Radio-Controlled Cars	\N	\N
235	\N	\N	Science Kit	Science kit with experiments and activities that teach basic science concepts	19.99	14.99	Science Explorers	\N	\N	\N	Science Kits	\N	\N
236	\N	\N	Scooter	Two-wheeled scooter with adjustable handlebars and a sturdy frame	49.99	39.99	Scooter Co	\N	\N	\N	Scooters	\N	\N
237	\N	\N	Squishy Toy	Soft and squeezable toy shaped like a fruit, animal, or other object	9.99	6.99	Squishy Toys	\N	\N	\N	Squishy Toys	\N	\N
238	\N	\N	Slime	Container of gooey and stretchy slime, for sensory play and stress relief	14.99	9.99	Slime Time	\N	\N	\N	Slime	\N	\N
239	\N	\N	Spinning Top	Classic toy that spins on its axis, with colorful designs and patterns	9.99	6.99	Top Spin	\N	\N	\N	Spinning Tops	\N	\N
240	\N	\N	Teddy Bear	Traditional teddy bear with soft fur and a cuddly design	19.99	14.99	Teddy Bears	\N	\N	\N	Teddy Bears	\N	\N
241	\N	\N	Tool Set	Toy tool set with tools like a hammer, screwdriver, and wrench, for imaginative play	14.99	9.99	Tool Time	\N	\N	\N	Tool Sets	\N	\N
242	\N	\N	Toy Car	Toy car with realistic details and features, like opening doors and working wheels	14.99	9.99	Car Zone	\N	\N	\N	Toy Cars	\N	\N
243	\N	\N	Toy Train	Set of toy train tracks and a train engine with cars, for imaginative play and storytelling	29.99	24.99	Train Town	\N	\N	\N	Toy Trains	\N	\N
244	\N	\N	Video Game	Video game for a specific gaming console, with various genres and storylines	39.99	29.99	Game Studios	\N	\N	\N	Video Games	\N	\N
245	\N	\N	Walkie-Talkie Set	Two-way walkie-talkie set for outdoor adventures and communication	19.99	14.99	Comms Corp	\N	\N	\N	Walkie-Talkies	\N	\N
246	\N	\N	Water Gun	Toy water gun with different spray settings and features	14.99	9.99	Water Warriors	\N	\N	\N	Water Guns	\N	\N
247	\N	\N	Writing Set	Set of pencils, crayons, and markers for writing, drawing, and coloring	14.99	9.99	Art Essentials	\N	\N	\N	Writing Sets	\N	\N
248	\N	\N	Barbie Dreamhouse	Three-story dollhouse with 10 rooms, elevator, and pool	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
249	\N	\N	Hot Wheels Ultimate Garage	Six-level garage with over 140 parking spaces	149.99	99.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
250	\N	\N	Nerf Fortnite BASR-L Blaster	Pump-action blaster with 6 darts	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
251	\N	\N	LEGO Star Wars Millennium Falcon	1,351-piece model of the iconic spaceship	199.99	149.99	LEGO	\N	\N	\N	Building Sets	\N	\N
252	\N	\N	American Girl Truly Me Doll	18-inch doll with customizable features	115.00	99.99	American Girl	\N	\N	\N	Dolls	\N	\N
253	\N	\N	Crayola Super Art Set	100-piece art set with crayons, markers, and paper	29.99	19.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
254	\N	\N	Melissa & Doug Magnetic Dress-Up Wooden Doll	Magnetic doll with interchangeable outfits	24.99	14.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
255	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Ice cream truck playset with over 20 accessories	49.99	39.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
256	\N	\N	Fortnite Battle Royale Squad Mode Action Figures	Set of 4 action figures based on the popular video game	29.99	19.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
257	\N	\N	Squishmallows 16-Inch Squishmallow	Soft and cuddly plush toy	19.99	14.99	Squishmallows	\N	\N	\N	Stuffed Animals	\N	\N
258	\N	\N	LOL Surprise! OMG House of Surprises	Three-story dollhouse with 8 rooms and 85+ surprises	199.99	149.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
259	\N	\N	Minecraft Dungeons Hero Edition	Video game that combines dungeon crawling with the Minecraft universe	29.99	19.99	Minecraft	\N	\N	\N	Gaming	\N	\N
260	\N	\N	Ravensburger Disney Villains Villainous Board Game	Strategy board game based on the Disney villains	39.99	29.99	Ravensburger	\N	\N	\N	Board Games	\N	\N
261	\N	\N	Harry Potter Hogwarts Castle	6,020-piece LEGO model of the iconic castle	399.99	299.99	LEGO	\N	\N	\N	Building Sets	\N	\N
262	\N	\N	Star Wars The Mandalorian The Child Animatronic Edition	Animatronic plush toy of Baby Yoda	59.99	49.99	Star Wars	\N	\N	\N	Stuffed Animals	\N	\N
263	\N	\N	Barbie Dreamtopia Rainbow Magic Unicorn	Unicorn with rainbow mane and tail	29.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
264	\N	\N	Hot Wheels Criss Cross Crash Track Set	Track set with multiple jumps and obstacles	39.99	29.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
265	\N	\N	Nerf Fortnite Pump SG Blaster	Shotgun-style blaster with 4 darts	29.99	19.99	Nerf	\N	\N	\N	Blasters	\N	\N
266	\N	\N	LEGO Minecraft The Nether Fortress	372-piece model of the Nether Fortress from Minecraft	29.99	24.99	LEGO	\N	\N	\N	Building Sets	\N	\N
267	\N	\N	American Girl WellieWishers Willa Doll	14-inch doll with a love for nature	55.00	49.99	American Girl	\N	\N	\N	Dolls	\N	\N
268	\N	\N	Crayola Color Wonder Mess-Free Coloring Pages	Set of 20 mess-free coloring pages	9.99	4.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
269	\N	\N	Melissa & Doug Wooden Activity Table	Activity table with 4 different play areas	79.99	59.99	Melissa & Doug	\N	\N	\N	Playsets	\N	\N
270	\N	\N	Play-Doh Kitchen Creations Ultimate Oven Playset	Playset with oven, utensils, and play food	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
271	\N	\N	Nintendo Switch Pro Controller	Wireless controller for the Nintendo Switch	69.99	59.99	Nintendo	\N	\N	\N	Gaming	\N	\N
272	\N	\N	Fortnite Victory Royale Series Midas Figure	6-inch action figure of the popular Fortnite character	19.99	14.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
273	\N	\N	Squishmallows 12-Inch Squishmallow	Soft and cuddly plush toy	14.99	9.99	Squishmallows	\N	\N	\N	Stuffed Animals	\N	\N
274	\N	\N	LOL Surprise! Tween Series 1 Neonlicious Doll	Fashion doll with 15+ surprises	39.99	29.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
275	\N	\N	Minecraft Dungeons Ultimate Edition	Video game that includes the base game and all DLC	49.99	39.99	Minecraft	\N	\N	\N	Gaming	\N	\N
276	\N	\N	Ravensburger Harry Potter Hogwarts Great Hall 3D Puzzle	3D puzzle of the Hogwarts Great Hall	34.99	24.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
277	\N	\N	Star Wars The Mandalorian Razor Crest	723-piece LEGO model of the Razor Crest spaceship	149.99	109.99	LEGO	\N	\N	\N	Building Sets	\N	\N
278	\N	\N	Barbie Chelsea Travel Doll and Playset	Travel-themed doll and playset	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
279	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm	Radio-controlled monster truck with Megalodon design	79.99	59.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
280	\N	\N	Nerf Fortnite Heavy SR Blaster	Sniper rifle-style blaster with 6 darts	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
281	\N	\N	Stuffed Teddy Bear Plush	Soft and cuddly teddy bear with a heart-shaped nose and embroidered eyes. Perfect for cuddling and imaginative play.	19.99	14.99	Teddy & Friends	\N	\N	\N	Stuffed Animals	\N	\N
282	\N	\N	Race Car Track Set	Complete race car track set with loops, jumps, and curves. Includes two race cars and a battery-operated launcher.	39.99	29.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
283	\N	\N	Building Blocks Set	Classic building blocks set with various shapes and colors. Encourages creativity, problem-solving, and fine motor skills.	24.99	19.99	LEGO	\N	\N	\N	Building Toys	\N	\N
284	\N	\N	Action Figure	Articulated action figure of a superhero with multiple points of articulation. Comes with accessories and a display stand.	14.99	9.99	Marvel	\N	\N	\N	Action Figures	\N	\N
285	\N	\N	Board Game	Fun and educational board game for the whole family. Includes a game board, dice, cards, and playing pieces.	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
286	\N	\N	Princess Doll	Beautiful princess doll with a flowing gown, tiara, and accessories. Perfect for imaginative play and storytelling.	24.99	19.99	Disney	\N	\N	\N	Dolls	\N	\N
287	\N	\N	Remote Control Car	Fast and furious remote control car with off-road capabilities. Features a sleek design and durable construction.	49.99	39.99	Traxxas	\N	\N	\N	Vehicles	\N	\N
288	\N	\N	Science Experiment Kit	Hands-on science experiment kit with materials and instructions for conducting various experiments. Sparks curiosity and encourages scientific exploration.	29.99	24.99	National Geographic	\N	\N	\N	Science & Nature	\N	\N
289	\N	\N	Arts & Crafts Kit	Creative arts and crafts kit with materials for painting, drawing, sculpting, and more. Encourages imagination and artistic expression.	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
290	\N	\N	Musical Instrument	Beginner-friendly musical instrument, such as a guitar, piano, or drum set. Encourages musical development and creativity.	49.99	39.99	Yamaha	\N	\N	\N	Musical Instruments	\N	\N
291	\N	\N	Nerf Gun	Powerful and accurate Nerf gun with a variety of ammo and accessories. Provides endless hours of active play.	19.99	14.99	Nerf	\N	\N	\N	Action Figures	\N	\N
292	\N	\N	Play Tent	Spacious and colorful play tent with windows and a door. Perfect for imaginative play, reading, and hide-and-seek.	24.99	19.99	Melissa & Doug	\N	\N	\N	Play Tents	\N	\N
293	\N	\N	Dress-Up Clothes	Assortment of dress-up clothes, such as princess gowns, superhero costumes, or animal masks. Encourages imagination and role-playing.	19.99	14.99	Melissa & Doug	\N	\N	\N	Dress-Up	\N	\N
294	\N	\N	Puzzle	Challenging and engaging puzzle with a variety of themes and difficulty levels. Improves problem-solving skills and concentration.	14.99	9.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
295	\N	\N	Slime Kit	Fun and gooey slime kit with ingredients and instructions for making different types of slime. Encourages creativity and sensory exploration.	19.99	14.99	Elmer's	\N	\N	\N	Science & Nature	\N	\N
296	\N	\N	Outdoor Playset	Complete outdoor playset with a swing, slide, climbing ladder, and other fun features. Promotes physical activity and gross motor skills.	79.99	59.99	Little Tikes	\N	\N	\N	Outdoor Play	\N	\N
297	\N	\N	Trampoline	Small trampoline with a safety net. Provides a fun and energetic way to get exercise.	99.99	79.99	JumpSport	\N	\N	\N	Outdoor Play	\N	\N
298	\N	\N	Ride-On Toy	Battery-powered ride-on car	199.99	149.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
299	\N	\N	Treehouse	Wooden treehouse with a platform, ladder, and windows. Perfect for outdoor adventures and imaginative play.	199.99	149.99	CedarWorks	\N	\N	\N	Outdoor Play	\N	\N
300	\N	\N	Dollhouse	Spacious and detailed dollhouse with multiple rooms, furniture, and accessories. Encourages imaginative play and storytelling.	99.99	79.99	KidKraft	\N	\N	\N	Dolls	\N	\N
301	\N	\N	Construction Vehicle Set	Set of construction vehicles, such as a dump truck, excavator, and bulldozer. Encourages imaginative play and fine motor skills.	29.99	24.99	Tonka	\N	\N	\N	Vehicles	\N	\N
302	\N	\N	Coding Robot	Interactive coding robot that teaches basic programming concepts through play. Encourages problem-solving and computational thinking.	79.99	59.99	Sphero	\N	\N	\N	Science & Nature	\N	\N
303	\N	\N	Chemistry Set	Complete chemistry set with materials and instructions for conducting various experiments. Sparks curiosity and encourages scientific exploration.	49.99	39.99	Thames & Kosmos	\N	\N	\N	Science & Nature	\N	\N
304	\N	\N	Telescope	Beginner-friendly telescope with a tripod and instructions. Provides an opportunity to explore the night sky and learn about astronomy.	99.99	79.99	Celestron	\N	\N	\N	Science & Nature	\N	\N
305	\N	\N	Microscope	Basic microscope with a light source and magnification lenses. Encourages scientific exploration and observation of tiny objects.	39.99	29.99	Carson	\N	\N	\N	Science & Nature	\N	\N
306	\N	\N	Remote Control Airplane	Easy-to-fly remote control airplane with a durable construction. Provides an exciting way to learn about aerodynamics.	49.99	39.99	Air Hogs	\N	\N	\N	Vehicles	\N	\N
307	\N	\N	Craft Beads	Assortment of craft beads in various shapes, sizes, and colors. Encourages creativity, fine motor skills, and jewelry making.	14.99	9.99	Hama	\N	\N	\N	Arts & Crafts	\N	\N
308	\N	\N	Jewelry Making Kit	Complete jewelry making kit with beads, wire, and tools. Encourages creativity and fine motor skills.	24.99	19.99	ALEX Toys	\N	\N	\N	Arts & Crafts	\N	\N
309	\N	\N	Slime Making Kit	Comprehensive slime making kit with ingredients and instructions for making different types of slime. Encourages creativity and sensory exploration.	19.99	14.99	Cra-Z-Art	\N	\N	\N	Science & Nature	\N	\N
310	\N	\N	Origami Paper Set	Pack of origami paper in various colors and patterns. Encourages creativity, fine motor skills, and spatial reasoning.	9.99	7.99	Origami USA	\N	\N	\N	Arts & Crafts	\N	\N
311	\N	\N	Magic Kit	Assortment of magic tricks with instructions and props. Provides entertainment and encourages problem-solving.	19.99	14.99	Melissa & Doug	\N	\N	\N	Games & Puzzles	\N	\N
312	\N	\N	Craft Foam Sheets	Pack of craft foam sheets in various colors and textures. Encourages creativity, fine motor skills, and model making.	14.99	9.99	Foamies	\N	\N	\N	Arts & Crafts	\N	\N
313	\N	\N	Mega Bloks Colossal Castle	Build a colossal castle with this Mega Bloks set! With over 1,000 pieces, this set is perfect for hours of creative play. The castle features a drawbridge, towers, and a dungeon, and comes with 10 knights and horses.	29.99	19.99	Mega Bloks	\N	\N	\N	Construction	\N	\N
314	\N	\N	Nerf Rival Prometheus MXVIII-20K	Unleash a storm of darts with the Nerf Rival Prometheus MXVIII-20K! This high-capacity blaster holds up to 200 rounds and fires at a rate of 8 rounds per second. With its adjustable stock and ergonomic grip, the Prometheus MXVIII-20K is perfect for both indoor and outdoor play.	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
315	\N	\N	LEGO Star Wars The Razor Crest	Build the iconic Razor Crest spacecraft from the hit TV show The Mandalorian! This LEGO set features over 1,000 pieces and includes minifigures of The Mandalorian, Grogu, Cara Dune, and Kuiil. The Razor Crest features a removable cockpit, cargo bay, and escape pod, and is perfect for imaginative play.	119.99	99.99	LEGO	\N	\N	\N	Building Toys	\N	\N
316	\N	\N	Barbie Dreamhouse	Every girl's dream! The Barbie Dreamhouse stands over 3 feet tall and features 10 rooms, including a kitchen, dining room, living room, bedroom, bathroom, and more. The Dreamhouse also comes with over 70 pieces of furniture and accessories, so your Barbie can live in style.	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
317	\N	\N	Hot Wheels Ultimate Garage	Park over 140 Hot Wheels cars in this massive Ultimate Garage! This playset features eight levels of parking, a spiral track, and a car wash. The Ultimate Garage also comes with 10 Hot Wheels cars, so you can start playing right away.	129.99	99.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
318	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Serve up some sweet treats with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck! This playset comes with everything you need to make your own Play-Doh ice cream, including a variety of molds, tools, and accessories. The Ultimate Ice Cream Truck also features a working cash register and drive-thru window, so you can play pretend and run your own ice cream business.	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
319	\N	\N	Melissa & Doug Wooden Activity Table	Encourage your child's creativity and imagination with the Melissa & Doug Wooden Activity Table! This table features a variety of activities, including a chalkboard, magnetic board, bead maze, and more. The Wooden Activity Table also comes with a set of 100 colorful wooden blocks, so your child can build and create to their heart's content.	49.99	39.99	Melissa & Doug	\N	\N	\N	Learning Toys	\N	\N
320	\N	\N	Crayola Ultimate Art Case	unleash your child's inner artist with the Crayola Ultimate Art Case! This case comes with over 150 pieces of art supplies, including crayons, markers, pencils, and paper. The Ultimate Art Case also features a built-in easel and storage compartments, so your child can keep all of their supplies organized and in one place.	49.99	39.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
321	\N	\N	LEGO Minecraft The Nether Fortress	Battle the fearsome Wither and other hostile mobs in the LEGO Minecraft The Nether Fortress! This set features over 500 pieces and includes minifigures of Steve, Alex, and a piglin. The Nether Fortress features a drawbridge, lava moat, and a variety of rooms to explore.	79.99	59.99	LEGO	\N	\N	\N	Building Toys	\N	\N
322	\N	\N	Fortnite Victory Royale Series Meowscles Action Figure	Join the battle with the Fortnite Victory Royale Series Meowscles Action Figure! This figure features over 20 points of articulation and comes with a variety of weapons and accessories. The Meowscles Action Figure is perfect for fans of the popular video game.	19.99	14.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
323	\N	\N	L.O.L. Surprise! OMG House of Surprises	Unbox over 85 surprises with the L.O.L. Surprise! OMG House of Surprises! This dollhouse features four floors, eight rooms, and a working elevator. The House of Surprises also comes with 12 exclusive L.O.L. Surprise! dolls, so you can create your own stories and adventures.	109.99	79.99	L.O.L. Surprise!	\N	\N	\N	Dolls	\N	\N
324	\N	\N	Paw Patrol Mighty Lookout Tower	Join the Paw Patrol pups on their exciting missions with the Mighty Lookout Tower! This playset features a working elevator, zip line, and lookout tower. The Mighty Lookout Tower also comes with six Paw Patrol figures, so you can play pretend and save the day.	69.99	49.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
325	\N	\N	Nintendo Switch Lite	Take your gaming on the go with the Nintendo Switch Lite! This portable console features a sleek design and a variety of colors to choose from. The Switch Lite plays all of your favorite Nintendo Switch games, so you can enjoy your favorite titles wherever you go.	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
326	\N	\N	Xbox Series S	Experience next-gen gaming with the Xbox Series S! This compact console features a sleek design and delivers amazing performance. The Xbox Series S plays all of your favorite Xbox games, so you can enjoy the latest and greatest titles in stunning 4K resolution.	299.99	249.99	Xbox	\N	\N	\N	Video Games	\N	\N
327	\N	\N	PlayStation 5 Digital Edition	Unleash the power of gaming with the PlayStation 5 Digital Edition! This console features a sleek design and delivers incredible performance. The PlayStation 5 Digital Edition plays all of your favorite PlayStation games, so you can enjoy the latest and greatest titles in stunning 4K resolution.	399.99	349.99	PlayStation	\N	\N	\N	Video Games	\N	\N
328	\N	\N	Apple iPad Air	Browse the web, watch videos, and play games on the Apple iPad Air! This tablet features a stunning 10.9-inch display and a powerful A14 Bionic chip. The iPad Air also comes with a variety of apps and features, so you can do everything you need and more.	599.99	499.99	Apple	\N	\N	\N	Tablets	\N	\N
329	\N	\N	Samsung Galaxy Tab S7	Experience next-level entertainment with the Samsung Galaxy Tab S7! This tablet features a stunning 11-inch display and a powerful Snapdragon 865+ processor. The Galaxy Tab S7 also comes with a variety of apps and features, so you can do everything you need and more.	699.99	599.99	Samsung	\N	\N	\N	Tablets	\N	\N
330	\N	\N	Beats Solo Pro Wireless Headphones	Enjoy your music in style with the Beats Solo Pro Wireless Headphones! These headphones feature a sleek design and deliver incredible sound quality. The Solo Pro Headphones also feature active noise cancellation, so you can block out the world and enjoy your music in peace.	299.99	249.99	Beats	\N	\N	\N	Headphones	\N	\N
331	\N	\N	Bose QuietComfort 35 II Wireless Headphones	Experience the ultimate in noise cancellation with the Bose QuietComfort 35 II Wireless Headphones! These headphones feature a sleek design and deliver incredible sound quality. The QuietComfort 35 II Headphones also feature three levels of noise cancellation, so you can find the perfect setting for your needs.	399.99	349.99	Bose	\N	\N	\N	Headphones	\N	\N
332	\N	\N	Apple Watch Series 6	Stay connected and healthy with the Apple Watch Series 6! This smartwatch features a stunning display, a powerful processor, and a variety of health and fitness tracking features. The Apple Watch Series 6 also comes with a variety of apps and features, so you can do everything you need and more.	399.99	349.99	Apple	\N	\N	\N	Smartwatches	\N	\N
333	\N	\N	Samsung Galaxy Watch 3	Manage your life and stay connected with the Samsung Galaxy Watch 3! This smartwatch features a sleek design, a powerful processor, and a variety of health and fitness tracking features. The Galaxy Watch 3 also comes with a variety of apps and features, so you can do everything you need and more.	399.99	349.99	Samsung	\N	\N	\N	Smartwatches	\N	\N
334	\N	\N	Fitbit Versa 3	Track your fitness and stay connected with the Fitbit Versa 3! This smartwatch features a sleek design, a powerful processor, and a variety of health and fitness tracking features. The Versa 3 also comes with a variety of apps and features, so you can do everything you need and more.	229.99	199.99	Fitbit	\N	\N	\N	Smartwatches	\N	\N
335	\N	\N	AirFort MegaFort	Giant inflatable indoor fort with air pump	39.99	29.99	AirFort	\N	\N	\N	Toys for 12yr+	\N	\N
336	\N	\N	LEGO Star Wars AT-AT Walker	Buildable AT-AT Walker with movable legs, head and cannons	149.99	119.99	LEGO	\N	\N	\N	Toys for 12yr+	\N	\N
337	\N	\N	Nerf Rival Prometheus MXVIII-20K Blaster	Fully-automatic Nerf blaster with 200-round capacity	79.99	59.99	Nerf	\N	\N	\N	Toys for 12yr+	\N	\N
338	\N	\N	Nintendo Switch Lite	Portable Nintendo Switch console	199.99	179.99	Nintendo	\N	\N	\N	Toys for 12yr+	\N	\N
339	\N	\N	Razor E100 Electric Scooter	Electric scooter for ages 8 and up	149.99	119.99	Razor	\N	\N	\N	Toys for 12yr+	\N	\N
340	\N	\N	Roblox Sharkbite Codes Bundle	Codes for virtual items in the Roblox game	19.99	14.99	Roblox	\N	\N	\N	Toys for 12yr+	\N	\N
341	\N	\N	Squishmallows 16-Inch Squishmallow	Plush toy in various animal designs	19.99	14.99	Squishmallows	\N	\N	\N	Toys for 12yr+	\N	\N
342	\N	\N	VTech KidiZoom Creator Cam	Digital camera for kids with built-in editing features	59.99	49.99	VTech	\N	\N	\N	Toys for 12yr+	\N	\N
343	\N	\N	Walkie Talkies for Kids	Pair of walkie talkies with a range of up to 3 miles	29.99	24.99	Walkie Talkies	\N	\N	\N	Toys for 12yr+	\N	\N
344	\N	\N	Barbie Dreamhouse	Multi-story dollhouse with multiple rooms and accessories	199.99	149.99	Barbie	\N	\N	\N	Toys for 12yr+	\N	\N
345	\N	\N	Beyblade Burst Turbo Spryzen	Beyblade top with a metal fusion core	19.99	14.99	Beyblade	\N	\N	\N	Toys for 12yr+	\N	\N
346	\N	\N	Build-A-Bear Workshop Teddy Bear	Customizable teddy bear with a variety of clothing and accessories	29.99	24.99	Build-A-Bear	\N	\N	\N	Toys for 12yr+	\N	\N
347	\N	\N	Cocomelon Interactive Learning JJ Doll	Interactive doll that sings songs and teaches phonics	39.99	29.99	Cocomelon	\N	\N	\N	Toys for 12yr+	\N	\N
348	\N	\N	Crayola Inspiration Art Case	Art case with a variety of art supplies	29.99	24.99	Crayola	\N	\N	\N	Toys for 12yr+	\N	\N
349	\N	\N	Disney Princess Ultimate Celebration Castle	Large playset with multiple rooms and Disney Princess characters	149.99	119.99	Disney	\N	\N	\N	Toys for 12yr+	\N	\N
350	\N	\N	Frozen 2 Elsa's Magical Ice Palace	Playset based on the Frozen 2 movie	79.99	59.99	Frozen	\N	\N	\N	Toys for 12yr+	\N	\N
351	\N	\N	Hot Wheels Ultimate Garage Playset	Multi-level playset with a variety of tracks and cars	199.99	149.99	Hot Wheels	\N	\N	\N	Toys for 12yr+	\N	\N
352	\N	\N	Imaginext DC Super Friends Batcave Playset	Playset based on the DC Super Friends franchise	79.99	59.99	Imaginext	\N	\N	\N	Toys for 12yr+	\N	\N
353	\N	\N	LOL Surprise! OMG House of Surprises	Multi-room dollhouse with over 85 surprises	149.99	119.99	LOL Surprise!	\N	\N	\N	Toys for 12yr+	\N	\N
354	\N	\N	Minecraft Dungeons Hero Edition	Game based on the Minecraft Dungeons franchise	29.99	24.99	Minecraft	\N	\N	\N	Toys for 12yr+	\N	\N
355	\N	\N	Nerf Fortnite BASR-L Blaster	Blaster based on the Fortnite video game	39.99	29.99	Nerf	\N	\N	\N	Toys for 12yr+	\N	\N
356	\N	\N	Nintendo Switch Joy-Con Charging Grip	Charging grip for Nintendo Switch Joy-Cons	29.99	24.99	Nintendo	\N	\N	\N	Toys for 12yr+	\N	\N
357	\N	\N	Paw Patrol Mighty Lookout Tower Playset	Playset based on the Paw Patrol TV show	79.99	59.99	Paw Patrol	\N	\N	\N	Toys for 12yr+	\N	\N
358	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Playset for making and decorating pretend ice cream	49.99	39.99	Play-Doh	\N	\N	\N	Toys for 12yr+	\N	\N
359	\N	\N	Roblox Adopt Me! Mega Neon Fly Ride Bat Dragon Plush	Plush toy based on the Roblox Adopt Me! game	39.99	29.99	Roblox	\N	\N	\N	Toys for 12yr+	\N	\N
360	\N	\N	Star Wars The Child Animatronic Edition	Animatronic toy based on the character The Child from The Mandalorian	59.99	49.99	Star Wars	\N	\N	\N	Toys for 12yr+	\N	\N
361	\N	\N	Super Mario Odyssey	Game based on the Super Mario franchise	59.99	49.99	Nintendo	\N	\N	\N	Toys for 12yr+	\N	\N
362	\N	\N	Teenage Mutant Ninja Turtles Lair Playset	Playset based on the Teenage Mutant Ninja Turtles franchise	99.99	79.99	Teenage Mutant Ninja Turtles	\N	\N	\N	Toys for 12yr+	\N	\N
363	\N	\N	VTech Switch & Go Dinos Grimlock the T-Rex	Transforming dinosaur toy	29.99	24.99	VTech	\N	\N	\N	Toys for 12yr+	\N	\N
364	\N	\N	Barbie Extra Minis Doll Playset	Playset with multiple mini Barbie dolls and accessories	19.99	14.99	Barbie	\N	\N	\N	Toys for 12yr+	\N	\N
365	\N	\N	Beyblade Burst Turbo Evolution Achilles	Beyblade top with a dual-layer design	19.99	14.99	Beyblade	\N	\N	\N	Toys for 12yr+	\N	\N
366	\N	\N	Build-A-Bear Workshop Rainbow Unicorn	Customizable unicorn bear with a variety of clothing and accessories	29.99	24.99	Build-A-Bear	\N	\N	\N	Toys for 12yr+	\N	\N
367	\N	\N	Cocomelon Musical Learning Cube	Interactive cube with songs, shapes and colors	39.99	29.99	Cocomelon	\N	\N	\N	Toys for 12yr+	\N	\N
368	\N	\N	Crayola Super Tips Washable Markers	Pack of 100 washable markers	29.99	24.99	Crayola	\N	\N	\N	Toys for 12yr+	\N	\N
369	\N	\N	Disney Pixar Cars Lightning McQueen Race & Go	Remote-controlled Lightning McQueen car	39.99	29.99	Disney	\N	\N	\N	Toys for 12yr+	\N	\N
370	\N	\N	Frozen 2 Elsa's Singing Snowflake Microphone	Microphone that plays Let It Go	29.99	24.99	Frozen	\N	\N	\N	Toys for 12yr+	\N	\N
371	\N	\N	Star Wars: Episode VII - The Force Awakens Black Series Kylo Ren 6-Inch Action Figure with Lightsaber	Kylo Ren, the powerful and enigmatic villain from Star Wars: Episode VII - The Force Awakens, comes to life in this incredible 6-inch action figure from the Black Series! This highly detailed figure features authentic styling and comes with a lightsaber accessory, so you can recreate all the epic action from the movie.	19.99	14.99	Star Wars	\N	\N	\N	Action Figure	\N	\N
372	\N	\N	Barbie Dreamhouse Adventures 3-Story Dollhouse with Pool, Slide & Elevator, 7 Rooms, 30+ Pieces Including Furniture & Accessories, for 3+ Year Olds	This Barbie dollhouse is the ultimate dream house for any Barbie fan! With 3 stories, 7 rooms, and over 30 pieces of furniture and accessories, there's plenty of space for Barbie and her friends to live, play, and explore. The house features a working elevator, a pool with a slide, and even a pet puppy!	29.99	24.99	Barbie	\N	\N	\N	Dollhouse	\N	\N
373	\N	\N	Hot Wheels Monster Trucks Live Glow in the Dark Bone Shaker Playset	Prepare for the ultimate monster truck experience with the Hot Wheels Monster Trucks Live Glow in the Dark Bone Shaker Playset! This awesome playset features a glow-in-the-dark Bone Shaker monster truck and a track with obstacles and jumps. You can even use the included launcher to send your monster truck racing around the track and crashing through obstacles.	24.99	19.99	Hot Wheels	\N	\N	\N	Playset	\N	\N
374	\N	\N	LEGO Star Wars Millennium Falcon Building Kit (75257), for Ages 9+	Relive the epic battles of Star Wars: Episode IV - A New Hope with this amazing LEGO Star Wars Millennium Falcon building kit! This highly detailed model features a rotating radar dish, lowering landing gear, opening cockpit, a working blaster cannon, and more. You can even recreate your favorite scenes from the movie with the included Han Solo, Chewbacca, Princess Leia, Luke Skywalker, and C-3PO minifigures.	149.99	129.99	LEGO	\N	\N	\N	Building Kit	\N	\N
375	\N	\N	NERF Fortnite BASR-L Blaster	Take your Fortnite game to the next level with the NERF Fortnite BASR-L Blaster! This blaster is inspired by the blaster used in the popular Fortnite video game and features a bolt-action mechanism for precision aiming. It also comes with 6 darts, so you can blast your opponents from afar.	19.99	14.99	NERF	\N	\N	\N	Blaster	\N	\N
376	\N	\N	Paw Patrol: The Movie Ultimate City Tower Playset	Join the Paw Patrol pups on their biggest adventure yet with the Paw Patrol: The Movie Ultimate City Tower Playset! This incredible playset features a 3-foot-tall tower with a working elevator, a zip line, a lookout tower, and more. It also comes with 6 Paw Patrol figures, so you can recreate all the exciting scenes from the movie.	59.99	49.99	Paw Patrol	\N	\N	\N	Playset	\N	\N
377	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Get ready for some sweet and silly fun with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset! This awesome playset comes with everything you need to create and serve your own pretend ice cream cones, sundaes, and more. You can even use the included molds and tools to create your own Play-Doh toppings and decorations.	29.99	24.99	Play-Doh	\N	\N	\N	Playset	\N	\N
378	\N	\N	Transformers: Generations War for Cybertron: Earthrise Deluxe WFC-E12 Hoist Action Figure	Roll out with the Transformers: Generations War for Cybertron: Earthrise Deluxe WFC-E12 Hoist Action Figure! This awesome figure converts from robot mode to vehicle mode in just 18 steps and comes with a variety of weapons and accessories. You can even combine this figure with other Transformers figures to form a powerful combiner.	19.99	14.99	Transformers	\N	\N	\N	Action Figure	\N	\N
379	\N	\N	Hot Wheels Super Mario Character Cars, 5-Pack	Race into the Mushroom Kingdom with the Hot Wheels Super Mario Character Cars, 5-Pack! This awesome pack includes 5 die-cast character cars featuring Mario, Luigi, Princess Peach, Bowser, and Toad. Each car is designed in the iconic style of the Super Mario video games and is perfect for racing and collecting.	14.99	10.99	Hot Wheels	\N	\N	\N	Character Cars	\N	\N
380	\N	\N	Barbie Dreamtopia Chelsea Mermaid Doll, 6.5-Inch, with Pink Hair and Teal Tail	Dive into a world of imagination with the Barbie Dreamtopia Chelsea Mermaid Doll! This beautiful doll features a long, pink hair and a sparkling teal tail. She also comes with a removable tiara and a matching seashell hairbrush.	12.99	9.99	Barbie	\N	\N	\N	Mermaid Doll	\N	\N
381	\N	\N	Hot Wheels Mario Kart Circuit Track Set	Get ready to race with the Hot Wheels Mario Kart Circuit Track Set! This awesome track set features a 2.5-foot-tall loop and multiple obstacles, so you can race your favorite Mario Kart characters to the finish line. You can even use the included launcher to send your cars racing around the track.	29.99	24.99	Hot Wheels	\N	\N	\N	Track Set	\N	\N
382	\N	\N	LEGO Marvel Spider-Man: Homecoming Attack on the Vulture Building Kit (76150), for Ages 8+	Join Spider-Man and Iron Man as they take on the Vulture in this thrilling LEGO Marvel Spider-Man: Homecoming Attack on the Vulture Building Kit! This awesome kit features a helicopter with rotating rotors, a car with stud shooters, and a building with a rooftop battle scene. You can even recreate your favorite scenes from the movie with the included Spider-Man, Iron Man, Vulture, and Aunt May minifigures.	49.99	39.99	LEGO	\N	\N	\N	Building Kit	\N	\N
383	\N	\N	Chemistry Set	Intermediate chemistry set with advanced experiments and materials, perfect for budding scientists.	149.99	119.99	ChemLab	\N	\N	\N	Science Toys	\N	\N
384	\N	\N	Stuffed Animal	Giant and cuddly stuffed animal, perfect for bedtime snuggles or imaginative play.	79.99	59.99	Cuddly Friends	\N	\N	\N	Stuffed Toys	\N	\N
385	\N	\N	Paw Patrol: The Movie Liberty Adventure Tower Playset	Join the Paw Patrol pups on their biggest adventure yet with the Paw Patrol: The Movie Liberty Adventure Tower Playset! This incredible playset features a 2-foot-tall tower with a working elevator, a zip line, a lookout tower, and more. It also comes with 6 Paw Patrol figures, so you can recreate all the exciting scenes from the movie.	39.99	29.99	Paw Patrol	\N	\N	\N	Playset	\N	\N
386	\N	\N	Barbie Fashionistas Doll #166, with Long Brunette Hair, Blue Eyes, and Floral Dress	Express your style with the Barbie Fashionistas Doll #166! This beautiful doll features long brunette hair, blue eyes, and a trendy floral dress. She also comes with a pair of shoes and a matching necklace.	10.99	7.99	Barbie	\N	\N	\N	Fashion Doll	\N	\N
387	\N	\N	Hot Wheels Monster Trucks 1:64 Scale Die-Cast Truck Assortment	Crush the competition with the Hot Wheels Monster Trucks 1:64 Scale Die-Cast Truck Assortment! This awesome assortment includes 5 different monster trucks, each with its own unique design and features. You can collect them all and build your own monster truck fleet.	2.99	1.99	Hot Wheels	\N	\N	\N	Monster Trucks	\N	\N
388	\N	\N	LEGO Friends Heartlake City Park (41426) Building Kit, for Ages 6+	Explore the fun and friendship of Heartlake City Park with the LEGO Friends Heartlake City Park (41426) Building Kit! This colorful kit features a slide, a swing, a seesaw, and a picnic area. You can even build a hot dog stand and a lemonade stand.	39.99	29.99	LEGO	\N	\N	\N	Building Kit	\N	\N
389	\N	\N	Play-Doh Kitchen Creations Ultimate Oven Playset	Become a master chef with the Play-Doh Kitchen Creations Ultimate Oven Playset! This awesome playset comes with everything you need to create and bake your own pretend cookies, cakes, and more. You can even use the included oven to bake your creations and decorate them with frosting and sprinkles.	29.99	24.99	Play-Doh	\N	\N	\N	Playset	\N	\N
390	\N	\N	Transformers: Generations War for Cybertron: Earthrise Voyager WFC-E23 Starscream Action Figure	Take to the skies with the Transformers: Generations War for Cybertron: Earthrise Voyager WFC-E23 Starscream Action Figure! This awesome figure converts from robot mode to jet mode in just 15 steps and comes with a variety of weapons and accessories. You can even combine this figure with other Transformers figures to form a powerful combiner.	29.99	24.99	Transformers	\N	\N	\N	Action Figure	\N	\N
391	\N	\N	Paw Patrol: The Movie Deluxe Transforming Ultimate City Cruiser Playset	Join the Paw Patrol pups on their biggest adventure yet with the Paw Patrol: The Movie Deluxe Transforming Ultimate City Cruiser Playset! This incredible playset features a transforming vehicle that converts from a police cruiser to a command center. It also comes with 6 Paw Patrol figures, so you can recreate all the exciting scenes from the movie.	69.99	59.99	Paw Patrol	\N	\N	\N	Playset	\N	\N
392	\N	\N	Hot Wheels id Smart Track Kit with 1 Race Portal, 1 Smart Car and 1 Charger	Experience the future of racing with the Hot Wheels id Smart Track Kit! This awesome kit includes a race portal, a smart car, and a charger. You can use the race portal to track your car's speed, laps, and more. You can even connect the kit to your smartphone to unlock new features and challenges.	39.99	29.99	Hot Wheels	\N	\N	\N	Track Kit	\N	\N
393	\N	\N	LEGO Minecraft The Nether Bastion (21185) Building Kit, for Ages 8+	Explore the dangerous Nether Bastion with the LEGO Minecraft The Nether Bastion (21185) Building Kit! This awesome kit features a fortress with a drawbridge, a lava moat, and a variety of hostile mobs. You can even build a wither boss to battle against.	59.99	49.99	LEGO	\N	\N	\N	Building Kit	\N	\N
394	\N	\N	Nerf Fortnite SMG-E Blaster	Get ready for some Fortnite action with the Nerf Fortnite SMG-E Blaster! This awesome blaster is inspired by the SMG-E blaster used in the popular Fortnite video game and features a rotating drum for fast-firing action. It also comes with 10 darts, so you can blast your opponents from afar.	19.99	14.99	Nerf	\N	\N	\N	Blaster	\N	\N
395	\N	\N	Barbie Dreamtopia Sparkle Lights Mermaid Doll, 12-Inch, with Pink Hair and Teal Tail	Dive into a world of imagination with the Barbie Dreamtopia Sparkle Lights Mermaid Doll! This beautiful doll features a long, pink hair and a sparkling teal tail. She also comes with a removable tiara and a matching seashell necklace.	19.99	14.99	Barbie	\N	\N	\N	Mermaid Doll	\N	\N
396	\N	\N	Hot Wheels Track Builder Unlimited Corkscrew Crash Track Set	Get ready for some gravity-defying action with the Hot Wheels Track Builder Unlimited Corkscrew Crash Track Set! This awesome set features a giant corkscrew loop, a crash zone, and a variety of track pieces. You can even use the included launcher to send your cars racing around the track and crashing through obstacles.	29.99	24.99	Hot Wheels	\N	\N	\N	Track Set	\N	\N
397	\N	\N	LEGO Harry Potter Hogwarts Chamber of Secrets (76389) Building Kit, for Ages 9+	Explore the iconic Hogwarts Chamber of Secrets with the LEGO Harry Potter Hogwarts Chamber of Secrets (76389) Building Kit! This awesome kit features a detailed model of the chamber, complete with the Basilisk, the Chamber of Secrets entrance, and a variety of accessories. You can even recreate your favorite scenes from the movie with the included Harry Potter, Ginny Weasley, Tom Riddle, and Luna Lovegood minifigures.	49.99	39.99	LEGO	\N	\N	\N	Building Kit	\N	\N
398	\N	\N	Paw Patrol: The Movie Lookout Tower Playset	Join the Paw Patrol pups on their biggest adventure yet with the Paw Patrol: The Movie Lookout Tower Playset! This incredible playset features a 3-foot-tall tower with a working elevator, a zip line, a lookout tower, and more. It also comes with 6 Paw Patrol figures, so you can recreate all the exciting scenes from the movie.	59.99	49.99	Paw Patrol	\N	\N	\N	Playset	\N	\N
399	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm Playset	Prepare for a monster truck showdown with the Hot Wheels Monster Trucks Live Megalodon Storm Playset! This awesome playset features a giant Megalodon monster truck and a track with obstacles and jumps. You can even use the included launcher to send your monster truck racing around the track and crashing through obstacles.	24.99	19.99	Hot Wheels	\N	\N	\N	Playset	\N	\N
400	\N	\N	Barbie Malibu House Playset with Pool, Slide, and Furniture	Welcome to the Barbie Malibu House! This awesome playset features a 3-story house with a pool, a slide, and a variety of furniture. You can even decorate the house with the included stickers and accessories.	59.99	49.99	Barbie	\N	\N	\N	Playset	\N	\N
401	\N	\N	Hot Wheels Super Mario Thwomp Ruins Track Set	Race through the Thwomp Ruins with the Hot Wheels Super Mario Thwomp Ruins Track Set! This awesome track set features a giant Thwomp and a variety of obstacles and jumps. You can even use the included launcher to send your Mario Kart cars racing around the track and crashing through obstacles.	29.99	24.99	Hot Wheels	\N	\N	\N	Track Set	\N	\N
402	\N	\N	LEGO Technic Monster Jam Max-D (42119) Building Kit, for Ages 7+	Build your own Monster Jam Max-D monster truck with the LEGO Technic Monster Jam Max-D (42119) Building Kit! This awesome kit features a pull-back motor, working suspension, and realistic details. You can even build a mini monster truck to race against.	39.99	29.99	LEGO	\N	\N	\N	Building Kit	\N	\N
403	\N	\N	Sports Ball	Professional-grade sports ball for soccer or basketball, perfect for serious athletes.	49.99	39.99	Sports Central	\N	\N	\N	Sports Toys	\N	\N
404	\N	\N	Paw Patrol: The Movie Transforming Air Patroller Playset	Join the Paw Patrol pups on their biggest adventure yet with the Paw Patrol: The Movie Transforming Air Patroller Playset! This incredible playset features a transforming vehicle that converts from a plane to a command center. It also comes with 6 Paw Patrol figures, so you can recreate all the exciting scenes from the movie.	69.99	59.99	Paw Patrol	\N	\N	\N	Playset	\N	\N
405	\N	\N	Hot Wheels Monster Trucks Live Glow in the Dark Night Saber Playset	Prepare for a glow-in-the-dark monster truck experience with the Hot Wheels Monster Trucks Live Glow in the Dark Night Saber Playset! This awesome playset features a glow-in-the-dark Night Saber monster truck and a track with obstacles and jumps. You can even use the included launcher to send your monster truck racing around the track and crashing through obstacles.	24.99	19.99	Hot Wheels	\N	\N	\N	Playset	\N	\N
406	\N	\N	LEGO Minecraft The Pig House (21170) Building Kit, for Ages 8+	Build your own Minecraft pig house with the LEGO Minecraft The Pig House (21170) Building Kit! This awesome kit features a detailed model of the pig house, complete with a pigsty, a garden, and a variety of accessories. You can even build a Creeper figure to add to the fun.	29.99	24.99	LEGO	\N	\N	\N	Building Kit	\N	\N
407	\N	\N	Barbie Dreamhouse Dollhouse with Pool, Slide & Elevator, 7 Rooms, 30+ Pieces Including Furniture & Accessories, for 3+ Year Olds	Welcome to the Barbie Dreamhouse! This awesome dollhouse features 3 stories, 7 rooms, and over 30 pieces of furniture and accessories. You can even decorate the house with the included stickers and accessories.	59.99	49.99	Barbie	\N	\N	\N	Dollhouse	\N	\N
408	\N	\N	Hot Wheels Super Mario Circuit Track Set	Get ready to race with the Hot Wheels Super Mario Circuit Track Set! This awesome track set features a 2.5-foot-tall loop and multiple obstacles, so you can race your favorite Mario Kart characters to the finish line. You can even use the included launcher to send your cars racing around the track.	29.99	24.99	Hot Wheels	\N	\N	\N	Track Set	\N	\N
409	\N	\N	Drone with Camera	High-quality drone with a built-in camera, perfect for capturing aerial footage and taking stunning photos.	399.99	299.99	Drones Hub	\N	\N	\N	Drones	\N	\N
410	\N	\N	Gaming Headset	Immersive gaming headset with surround sound and a comfortable fit, ideal for intense gaming sessions.	149.99	99.99	Headset Corp	\N	\N	\N	Headsets	\N	\N
411	\N	\N	Interactive Robot	Advanced interactive robot that can sing, dance, and respond to commands, providing hours of entertainment.	199.99	149.99	RoboTech	\N	\N	\N	Robots	\N	\N
412	\N	\N	Nerf Gun	High-powered Nerf gun with multiple firing modes, perfect for thrilling outdoor battles.	49.99	39.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
413	\N	\N	RC Car	Fast and agile RC car with off-road capabilities, ideal for racing or exploring bumpy terrain.	129.99	99.99	RC Nation	\N	\N	\N	RC Cars	\N	\N
414	\N	\N	Building Blocks	Massive set of colorful building blocks that encourage creativity and imagination.	79.99	59.99	Block City	\N	\N	\N	Building Toys	\N	\N
415	\N	\N	Board Game	Classic board game that combines strategy, skill, and a bit of luck, perfect for family game nights.	39.99	29.99	Board Game Central	\N	\N	\N	Board Games	\N	\N
416	\N	\N	Art Supplies	Complete set of art supplies including paints, brushes, paper, and pencils, perfect for budding artists.	129.99	99.99	Art Essentials	\N	\N	\N	Arts & Crafts	\N	\N
417	\N	\N	Science Kit	Comprehensive science kit with experiments and activities that explore the wonders of science.	99.99	79.99	Science Quest	\N	\N	\N	Science Toys	\N	\N
418	\N	\N	Dollhouse	Elaborate dollhouse with multiple rooms and furniture, perfect for imaginative play.	199.99	149.99	Dollhouse Dreams	\N	\N	\N	Dollhouses	\N	\N
419	\N	\N	Action Figure	Highly detailed action figure of a popular superhero, perfect for collectors or imaginative play.	49.99	39.99	Superhero Toys	\N	\N	\N	Action Figures	\N	\N
420	\N	\N	Chemistry Set	Safe and educational chemistry set that allows kids to explore the basics of chemistry.	79.99	59.99	ChemLab	\N	\N	\N	Science Toys	\N	\N
421	\N	\N	Stuffed Animal	Soft and cuddly stuffed animal, perfect for bedtime snuggles or imaginative play.	39.99	29.99	Cuddly Friends	\N	\N	\N	Stuffed Toys	\N	\N
422	\N	\N	Sports Ball	High-quality sports ball for basketball, soccer, or football, perfect for active play.	29.99	19.99	Sports Central	\N	\N	\N	Sports Toys	\N	\N
423	\N	\N	Musical Instrument	Beginner-friendly musical instrument such as a guitar or keyboard, perfect for introducing kids to music.	99.99	79.99	Music Masters	\N	\N	\N	Musical Toys	\N	\N
424	\N	\N	Construction Set	Large construction set with bricks, beams, and wheels, perfect for building and creating.	149.99	119.99	BuildTech	\N	\N	\N	Building Toys	\N	\N
425	\N	\N	Educational Game	Fun and educational game that teaches kids about science, math, or language.	59.99	49.99	Learning Labs	\N	\N	\N	Educational Toys	\N	\N
426	\N	\N	Magic Kit	Exciting magic kit with easy-to-follow tricks, perfect for aspiring young magicians.	49.99	39.99	Magic Moments	\N	\N	\N	Magic Toys	\N	\N
427	\N	\N	Puzzles	Challenging puzzles of various sizes and difficulty levels, perfect for brain teasers and family fun.	29.99	19.99	Puzzle Palace	\N	\N	\N	Puzzles & Games	\N	\N
428	\N	\N	Slime Kit	Non-toxic slime kit with glitter, colors, and scents, perfect for messy and creative play.	39.99	29.99	Slime Zone	\N	\N	\N	Arts & Crafts	\N	\N
429	\N	\N	Craft Kit	Craft kit with materials and instructions for making unique and personalized items.	59.99	49.99	Craft Central	\N	\N	\N	Arts & Crafts	\N	\N
430	\N	\N	Science Fair Project Kit	Comprehensive science fair project kit with materials and instructions for a variety of experiments.	99.99	79.99	ScienceQuest	\N	\N	\N	Science Toys	\N	\N
431	\N	\N	Gardening Kit	Complete gardening kit with seeds, tools, and a planter, perfect for aspiring young gardeners.	49.99	39.99	Green Thumbs	\N	\N	\N	Outdoor Toys	\N	\N
432	\N	\N	Building Blocks	Colorful and interactive building blocks with different shapes and sizes, perfect for developing fine motor skills.	39.99	29.99	Block City	\N	\N	\N	Building Toys	\N	\N
433	\N	\N	Board Game	Fast-paced and strategic board game that combines luck and skill, perfect for family game nights.	29.99	19.99	Game Factory	\N	\N	\N	Board Games	\N	\N
434	\N	\N	Art Supplies	Versatile art supplies with a wide range of colors and tools, perfect for exploring creativity.	99.99	79.99	Art Essentials	\N	\N	\N	Arts & Crafts	\N	\N
435	\N	\N	Science Kit	Hands-on science kit that allows kids to explore the wonders of physics.	79.99	59.99	Science Quest	\N	\N	\N	Science Toys	\N	\N
436	\N	\N	Dollhouse	Charming dollhouse with exquisite details and furniture, perfect for imaginative play.	249.99	199.99	Dollhouse Dreams	\N	\N	\N	Dollhouses	\N	\N
437	\N	\N	Action Figure	Highly detailed action figure of a popular video game character, perfect for collectors or imaginative play.	69.99	59.99	Game Heroes	\N	\N	\N	Action Figures	\N	\N
438	\N	\N	Bath Toys	Set of bath squirters in the shape of sea animals	10.99	7.99	Playskool	\N	\N	\N	Bath Toys	\N	\N
439	\N	\N	Musical Instrument	Intermediate musical instrument such as a saxophone or violin, perfect for developing musical skills.	199.99	149.99	Music Masters	\N	\N	\N	Musical Toys	\N	\N
440	\N	\N	Construction Set	Advanced construction set with gears, motors, and sensors, perfect for building complex creations.	249.99	199.99	BuildTech	\N	\N	\N	Building Toys	\N	\N
441	\N	\N	Educational Game	Immersive educational game that combines technology and learning, perfect for fostering STEM skills.	99.99	79.99	Learning Labs	\N	\N	\N	Educational Toys	\N	\N
442	\N	\N	Magic Kit	Advanced magic kit with captivating illusions and tricks, perfect for aspiring young magicians.	89.99	69.99	Magic Moments	\N	\N	\N	Magic Toys	\N	\N
443	\N	\N	Building Blocks	Assortment of colorful building blocks for imaginative play.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
444	\N	\N	Dollhouse	Charming dollhouse with multiple rooms and furniture.	49.99	39.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
445	\N	\N	Action Figure Set	Set of superhero action figures with capes and accessories.	29.99	24.99	Marvel	\N	\N	\N	Action Figures	\N	\N
446	\N	\N	Play Kitchen	Interactive kitchen set with pretend appliances and food.	34.99	29.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
447	\N	\N	Ride-On Car	Colorful and sturdy ride-on car for outdoor play.	24.99	19.99	Little Tikes	\N	\N	\N	Ride-On Toys	\N	\N
448	\N	\N	Stuffed Animal	Soft and cuddly stuffed animal for comfort and companionship.	14.99	11.99	Teddy Bear	\N	\N	\N	Stuffed Animals	\N	\N
449	\N	\N	Musical Instrument Set	Assortment of musical instruments for musical exploration.	29.99	24.99	Fisher-Price	\N	\N	\N	Musical Toys	\N	\N
450	\N	\N	Art Supplies	Box of crayons, markers, and paper for creative expression.	12.99	9.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
451	\N	\N	Puzzle Set	Variety of puzzles with different themes and difficulty levels.	19.99	14.99	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
452	\N	\N	Board Game	Classic board game for family fun and strategy.	24.99	19.99	Monopoly	\N	\N	\N	Board Games	\N	\N
453	\N	\N	Bath Toys	Assortment of floating and squirting toys for bath time fun.	14.99	11.99	Munchkin	\N	\N	\N	Bath Toys	\N	\N
454	\N	\N	Play Tent	Spacious and colorful play tent for indoor adventures.	29.99	24.99	Melissa & Doug	\N	\N	\N	Play Structures	\N	\N
455	\N	\N	Sandpit	Durable sandpit with lid for outdoor sensory play.	49.99	39.99	Little Tikes	\N	\N	\N	Outdoor Play	\N	\N
456	\N	\N	Water Table	Interactive water table with water jets and accessories.	39.99	34.99	Step2	\N	\N	\N	Water Toys	\N	\N
457	\N	\N	Trampoline	Compact trampoline for indoor and outdoor exercise.	99.99	79.99	JumpSport	\N	\N	\N	Exercise Toys	\N	\N
458	\N	\N	Balance Bike	Two-wheeled balance bike for developing motor skills.	79.99	69.99	Strider	\N	\N	\N	Ride-On Toys	\N	\N
459	\N	\N	Scooter	Foldable scooter for outdoor fun and exploration.	49.99	39.99	Razor	\N	\N	\N	Ride-On Toys	\N	\N
460	\N	\N	Remote Control Car	High-speed remote control car for thrilling races.	39.99	34.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
461	\N	\N	Drone	Beginner-friendly drone with easy controls and obstacle avoidance.	99.99	79.99	DJI	\N	\N	\N	Remote Control Toys	\N	\N
462	\N	\N	Electronic Learning Tablet	Interactive tablet with educational games and activities.	79.99	69.99	LeapFrog	\N	\N	\N	Educational Toys	\N	\N
463	\N	\N	Coding Robot	Educational robot that teaches coding concepts through play.	149.99	119.99	Sphero	\N	\N	\N	Educational Toys	\N	\N
464	\N	\N	Science Kit	Engaging science kit with hands-on experiments and demonstrations.	49.99	39.99	National Geographic	\N	\N	\N	Educational Toys	\N	\N
465	\N	\N	Building Blocks (Pink)	Assortment of pink building blocks for imaginative play.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
466	\N	\N	Dollhouse (Princess)	Charming princess-themed dollhouse with multiple rooms and furniture.	49.99	39.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
467	\N	\N	Action Figure Set (Princess)	Set of princess action figures with accessories.	29.99	24.99	Disney	\N	\N	\N	Action Figures	\N	\N
468	\N	\N	Play Kitchen (Pink)	Interactive pink kitchen set with pretend appliances and food.	34.99	29.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
469	\N	\N	Ride-On Car (Princess)	Colorful and sturdy princess-themed ride-on car for outdoor play.	24.99	19.99	Little Tikes	\N	\N	\N	Ride-On Toys	\N	\N
470	\N	\N	Stuffed Animal (Unicorn)	Soft and cuddly unicorn stuffed animal for comfort and companionship.	14.99	11.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
471	\N	\N	Musical Instrument Set (Pink)	Assortment of pink musical instruments for musical exploration.	29.99	24.99	Fisher-Price	\N	\N	\N	Musical Toys	\N	\N
472	\N	\N	Art Supplies (Pink)	Box of crayons, markers, and paper in pink for creative expression.	12.99	9.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
473	\N	\N	Puzzle Set (Pink)	Variety of pink puzzles with different themes and difficulty levels.	19.99	14.99	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
474	\N	\N	Board Game (Candy Land)	Classic and colorful board game for sweet adventures.	24.99	19.99	Hasbro	\N	\N	\N	Board Games	\N	\N
475	\N	\N	Dollhouse	Three-story wooden dollhouse with furniture and accessories.	49.99	39.99	Melissa & Doug	\N	\N	\N	Dolls & Accessories	\N	\N
476	\N	\N	Train Set	Electric train set with tracks, train engine, and cars.	79.99	59.99	Lionel	\N	\N	\N	Trains	\N	\N
477	\N	\N	Building Blocks	Set of 100 colorful wooden building blocks.	19.99	14.99	Melissa & Doug	\N	\N	\N	Building Toys	\N	\N
478	\N	\N	Play Kitchen	Wooden play kitchen with stove, oven, sink, and accessories.	99.99	79.99	Step2	\N	\N	\N	Pretend Play	\N	\N
479	\N	\N	Sand Table	Plastic sand table with lid and accessories.	49.99	34.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
480	\N	\N	Ride-On Car	Battery-powered ride-on car with remote control.	199.99	149.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
481	\N	\N	Play Tent	Foldable play tent with mesh windows and door.	29.99	19.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
482	\N	\N	Art Easel	Double-sided art easel with paper roll, markers, and crayons.	39.99	29.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
483	\N	\N	Toy Chest	Wooden toy chest with hinged lid and safety lock.	49.99	39.99	Step2	\N	\N	\N	Storage	\N	\N
484	\N	\N	Puppet Theater	Wooden puppet theater with curtains and stage.	59.99	44.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
485	\N	\N	Musical Instrument Set	Set of 5 musical instruments including a drum, xylophone, and tambourine.	29.99	19.99	Playskool	\N	\N	\N	Musical Toys	\N	\N
486	\N	\N	Science Kit	Hands-on science kit with experiments and activities.	39.99	29.99	National Geographic	\N	\N	\N	Educational Toys	\N	\N
487	\N	\N	Construction Set	Set of 100 plastic construction pieces.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
488	\N	\N	Pretend Food Set	Set of plastic pretend food including fruits, vegetables, and meats.	19.99	14.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
491	\N	\N	Board Game	Classic board game for 2-4 players.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
492	\N	\N	Card Game	Deck of 52 playing cards.	9.99	6.99	Bicycle	\N	\N	\N	Card Games	\N	\N
493	\N	\N	Puzzle	100-piece jigsaw puzzle with a colorful image.	19.99	14.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
494	\N	\N	Stuffed Animal	Soft and cuddly stuffed animal in various animal shapes.	14.99	9.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
495	\N	\N	Remote Control Car	Radio-controlled car with rechargeable battery.	99.99	79.99	Traxxas	\N	\N	\N	Remote Control Toys	\N	\N
496	\N	\N	Video Game	Adventure video game for all ages.	59.99	44.99	Nintendo	\N	\N	\N	Video Games	\N	\N
497	\N	\N	Tablet	Kid-friendly tablet with educational apps and games.	99.99	79.99	LeapFrog	\N	\N	\N	Educational Toys	\N	\N
498	\N	\N	Tricycle	Three-wheeled tricycle with a basket and bell.	79.99	59.99	Schwinn	\N	\N	\N	Ride-On Toys	\N	\N
499	\N	\N	Scooter	Two-wheeled scooter with adjustable handlebars.	49.99	34.99	Razor	\N	\N	\N	Ride-On Toys	\N	\N
500	\N	\N	Bicycle	16-inch bicycle with training wheels and a helmet.	129.99	99.99	Huffy	\N	\N	\N	Ride-On Toys	\N	\N
501	\N	\N	Trampoline	10-foot trampoline with safety net.	299.99	249.99	JumpSport	\N	\N	\N	Outdoor Toys	\N	\N
502	\N	\N	Swing Set	Metal swing set with two swings and a slide.	199.99	149.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
503	\N	\N	Water Table	Plastic water table with water toys and accessories.	49.99	34.99	Step2	\N	\N	\N	Outdoor Toys	\N	\N
504	\N	\N	Sandpit	Large plastic sandpit with cover.	99.99	79.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
505	\N	\N	Playhouse	Wooden playhouse with a door and windows.	299.99	249.99	Step2	\N	\N	\N	Outdoor Toys	\N	\N
506	\N	\N	Fort	Pop-up fort with mesh windows and door.	49.99	39.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
507	\N	\N	Craft Kit	Set of craft supplies including paper, markers, and glue.	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
508	\N	\N	Science Experiment Kit	Hands-on science experiment kit with instructions.	29.99	19.99	National Geographic	\N	\N	\N	Educational Toys	\N	\N
509	\N	\N	Building Blocks Set	Set of 50 foam building blocks in various shapes and colors.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
510	\N	\N	Animal Figurines	Set of 12 realistic animal figurines.	29.99	19.99	Schleich	\N	\N	\N	Animal Toys	\N	\N
511	\N	\N	Toy Car	Red and blue toy car with realistic sounds and lights	10.99	8.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
512	\N	\N	Doll House	Pink and white doll house with 3 levels and multiple rooms	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
513	\N	\N	Building Blocks	Set of 100 colorful building blocks in various shapes	12.99	9.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
514	\N	\N	Stuffed Animal	Soft and cuddly brown teddy bear with a red bow	14.99	10.99	Teddy Bear	\N	\N	\N	Stuffed Animals	\N	\N
515	\N	\N	Action Figure	Superman action figure with movable joints and cape	10.99	7.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
516	\N	\N	Play Kitchen	Pink and white play kitchen with sink, stove, and oven	29.99	24.99	Little Tikes	\N	\N	\N	Pretend Play	\N	\N
517	\N	\N	Board Game	Candy Land board game with colorful path and sweet treats	14.99	10.99	Hasbro	\N	\N	\N	Board Games	\N	\N
518	\N	\N	Musical Instrument	Pink and blue toy piano with 8 keys and realistic sounds	19.99	14.99	Playskool	\N	\N	\N	Musical Toys	\N	\N
519	\N	\N	Art Supplies	Set of crayons, markers, and paper in a carrying case	10.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
520	\N	\N	Science Kit	Volcano science kit with baking soda and vinegar	14.99	10.99	National Geographic	\N	\N	\N	Science Toys	\N	\N
521	\N	\N	Puzzles	Set of 100 piece jigsaw puzzles with animal designs	12.99	9.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
522	\N	\N	Ride-On Toy	Blue and white ride-on car with pedals	29.99	24.99	Radio Flyer	\N	\N	\N	Ride-On Toys	\N	\N
523	\N	\N	Dress-Up Clothes	Set of princess dress-up clothes with tiara and wand	19.99	14.99	Melissa & Doug	\N	\N	\N	Dress-Up Clothes	\N	\N
524	\N	\N	Video Game	Super Mario Bros. video game for Nintendo Switch	39.99	29.99	Nintendo	\N	\N	\N	Video Games	\N	\N
525	\N	\N	Books	Set of 3 hardcover books with fairy tales	14.99	10.99	Disney	\N	\N	\N	Books	\N	\N
526	\N	\N	Sports Equipment	Mini basketball hoop with adjustable height	19.99	14.99	Little Tikes	\N	\N	\N	Sports Toys	\N	\N
527	\N	\N	Electronics	Pink and white toy laptop with pretend keyboard and mouse	29.99	24.99	VTech	\N	\N	\N	Electronics	\N	\N
528	\N	\N	Outdoor Toys	Blue and green swing set with slide	99.99	79.99	Step2	\N	\N	\N	Outdoor Toys	\N	\N
529	\N	\N	Bath Toys	Set of rubber duckies in various colors and shapes	10.99	7.99	Skip Hop	\N	\N	\N	Bath Toys	\N	\N
530	\N	\N	Pretend Play	Doctor's kit with stethoscope, syringe, and bandage	19.99	14.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
531	\N	\N	Musical Instruments	Set of wooden musical instruments including xylophone, drums, and tambourine	29.99	24.99	Hape	\N	\N	\N	Musical Toys	\N	\N
532	\N	\N	Construction Toys	Set of plastic building blocks with gears and pulleys	19.99	14.99	Gears! Gears! Gears!	\N	\N	\N	Construction Toys	\N	\N
533	\N	\N	Dolls	Brown and white baby doll with soft body and movable limbs	29.99	24.99	American Girl	\N	\N	\N	Dolls	\N	\N
534	\N	\N	Science Toys	Chemistry set with test tubes, beakers, and chemicals	29.99	24.99	National Geographic	\N	\N	\N	Science Toys	\N	\N
535	\N	\N	Puzzles	Set of 200 piece jigsaw puzzles with animal designs	14.99	10.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
536	\N	\N	Ride-On Toys	Red and yellow ride-on motorcycle with battery-powered engine	99.99	79.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
537	\N	\N	Dress-Up Clothes	Set of superhero dress-up clothes with cape and mask	19.99	14.99	Rubie's	\N	\N	\N	Dress-Up Clothes	\N	\N
538	\N	\N	Video Games	Minecraft video game for Xbox One	29.99	24.99	Mojang	\N	\N	\N	Video Games	\N	\N
539	\N	\N	Books	Set of 4 hardcover books with classic fairy tales	19.99	14.99	Grimm Brothers	\N	\N	\N	Books	\N	\N
540	\N	\N	Sports Toys	Blue and white soccer ball with official size and weight	14.99	10.99	Adidas	\N	\N	\N	Sports Toys	\N	\N
541	\N	\N	Electronics	Green and blue toy tablet with touch screen and educational apps	39.99	29.99	LeapFrog	\N	\N	\N	Electronics	\N	\N
542	\N	\N	Outdoor Toys	Yellow and blue trampoline with safety net	199.99	149.99	JumpSport	\N	\N	\N	Outdoor Toys	\N	\N
543	\N	\N	Plush Unicorn with Glitter	Large plush unicorn with shiny silver glitter fabric and a rainbow mane and tail.	24.99	19.99	Aurora	\N	\N	\N	Stuffed Animals	\N	\N
544	\N	\N	Interactive Toy Robot	Robot toy that can walk, talk, and sing. Comes with a remote control.	49.99	39.99	WowWee	\N	\N	\N	Robotics	\N	\N
545	\N	\N	Wooden Train Set	30-piece wooden train set with tracks, trains, and accessories.	34.99	29.99	Melissa & Doug	\N	\N	\N	Wooden Toys	\N	\N
546	\N	\N	Princess Dress-Up Set	Dress-up set includes a gown, tiara, wand, and shoes.	29.99	24.99	Disney	\N	\N	\N	Dress-Up	\N	\N
547	\N	\N	Remote Control Car	RC car with a sleek design and high-speed motor.	39.99	34.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
548	\N	\N	Play Kitchen Set	Kitchen play set with stove, oven, refrigerator, and sink.	79.99	69.99	Step2	\N	\N	\N	Playhouses	\N	\N
549	\N	\N	Magnetic Building Blocks	Magnetic building blocks in various shapes and colors.	44.99	39.99	Magformers	\N	\N	\N	Building Toys	\N	\N
550	\N	\N	Nerf Gun	Nerf gun that shoots foam darts.	19.99	14.99	Hasbro	\N	\N	\N	Outdoor Toys	\N	\N
551	\N	\N	Board Game for Kids	Children's board game that teaches counting and colors.	14.99	11.99	Ravensburger	\N	\N	\N	Board Games	\N	\N
552	\N	\N	Art Supplies Set	Art supplies set with crayons, markers, and paints.	24.99	19.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
553	\N	\N	Dollhouse with Furniture	Dollhouse with multiple rooms and furniture pieces.	59.99	49.99	Barbie	\N	\N	\N	Dolls	\N	\N
554	\N	\N	Play Tent	Foldable play tent with a fun animal design.	29.99	24.99	Melissa & Doug	\N	\N	\N	Playhouses	\N	\N
555	\N	\N	Lego Building Set	Lego building set with bricks in various colors and shapes.	34.99	29.99	Lego	\N	\N	\N	Building Toys	\N	\N
556	\N	\N	Stuffed Animal Bear	Soft and cuddly stuffed animal bear.	19.99	14.99	Teddy Bear	\N	\N	\N	Stuffed Animals	\N	\N
557	\N	\N	Play Mat with Animals	Play mat with colorful animal designs.	24.99	19.99	Skip Hop	\N	\N	\N	Baby Toys	\N	\N
558	\N	\N	Sand and Water Play Table	Table with two compartments for sand and water play.	49.99	39.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
559	\N	\N	Ride-On Toy Car	Ride-on toy car with a steering wheel and horn.	39.99	34.99	Fisher-Price	\N	\N	\N	Vehicles	\N	\N
560	\N	\N	Construction Vehicle Set	Set of construction vehicles, including a dump truck, excavator, and bulldozer.	34.99	29.99	Tonka	\N	\N	\N	Vehicles	\N	\N
561	\N	\N	Craft Kit for Kids	Craft kit with materials for making jewelry, slime, or other crafts.	19.99	14.99	Creativity for Kids	\N	\N	\N	Arts & Crafts	\N	\N
562	\N	\N	Puzzle for Kids	Puzzle with large pieces designed for young children.	14.99	11.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
563	\N	\N	Action Figure	Action figure of a popular superhero or character.	19.99	14.99	Hasbro	\N	\N	\N	Action Figures	\N	\N
564	\N	\N	Toy Cash Register	Toy cash register with a scanner, drawer, and play money.	29.99	24.99	Melissa & Doug	\N	\N	\N	Playhouses	\N	\N
565	\N	\N	Musical Instrument Set	Set of musical instruments, including a drum, xylophone, and tambourine.	34.99	29.99	Melissa & Doug	\N	\N	\N	Musical Toys	\N	\N
566	\N	\N	Building Blocks for Toddlers	Large building blocks designed for toddlers.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
567	\N	\N	Interactive Learning Tablet	Tablet with educational games and activities.	49.99	39.99	LeapFrog	\N	\N	\N	Learning Toys	\N	\N
568	\N	\N	Art Easel for Kids	Art easel with a whiteboard and paper roll.	34.99	29.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
569	\N	\N	Slime Kit for Kids	Slime kit with materials for making and playing with slime.	19.99	14.99	Elmer's	\N	\N	\N	Arts & Crafts	\N	\N
570	\N	\N	Science Experiment Kit	Science experiment kit with materials for conducting simple experiments.	29.99	24.99	National Geographic	\N	\N	\N	Learning Toys	\N	\N
571	\N	\N	Pretend Play Food Set	Play food set with realistic-looking fruits, vegetables, and meats.	24.99	19.99	Melissa & Doug	\N	\N	\N	Playhouses	\N	\N
572	\N	\N	Playdough Bucket	Bucket of playdough in various colors.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
573	\N	\N	Toy Tool Set	Toy tool set with a hammer, screwdriver, and wrench.	24.99	19.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
574	\N	\N	Play Kitchen Appliance Set	Play kitchen appliance set with a refrigerator, stove, and oven.	49.99	39.99	Little Tikes	\N	\N	\N	Playhouses	\N	\N
575	\N	\N	Magnetic Drawing Board	Magnetic drawing board with a stylus.	19.99	14.99	Melissa & Doug	\N	\N	\N	Arts & Crafts	\N	\N
576	\N	\N	Doll with Accessories	Doll with a variety of clothing and accessories.	59.99	49.99	American Girl	\N	\N	\N	Dolls	\N	\N
577	\N	\N	Nerf N-Strike Elite Firestrike Blaster	The Nerf N-Strike Elite Firestrike Blaster is a single-shot blaster that fires darts up to 75 feet. It has a quick-load design and a tactical rail for accessories.	14.99	11.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
578	\N	\N	Barbie Dreamhouse	The Barbie Dreamhouse is a three-story dollhouse with 10 rooms, a working elevator, and a pool. It comes with over 70 pieces of furniture and accessories.	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
579	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Kit	The Hot Wheels Track Builder Unlimited Triple Loop Kit lets you create your own custom tracks. It comes with over 50 pieces of track, including loops, curves, and jumps.	49.99	39.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
580	\N	\N	Lego Star Wars Millennium Falcon	The Lego Star Wars Millennium Falcon is a detailed replica of the iconic spaceship from the Star Wars movies. It has over 7,500 pieces and comes with 6 minifigures.	799.99	699.99	Lego	\N	\N	\N	Building Toys	\N	\N
581	\N	\N	Paw Patrol Lookout Tower	The Paw Patrol Lookout Tower is a playset based on the popular TV show. It has a working elevator, a zip line, and a lookout tower with a 360-degree view.	99.99	79.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
582	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	The Play-Doh Kitchen Creations Ultimate Ice Cream Truck is a playset that lets kids create their own ice cream treats. It comes with over 25 pieces, including an ice cream maker, a cash register, and a variety of Play-Doh colors.	29.99	24.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
583	\N	\N	My Little Pony Rainbow Dash Figure	The My Little Pony Rainbow Dash Figure is a 6-inch figure of the popular character from the My Little Pony TV show. It comes with a removable headband and wings.	14.99	11.99	My Little Pony	\N	\N	\N	Figures	\N	\N
584	\N	\N	Transformers Bumblebee Action Figure	The Transformers Bumblebee Action Figure is a 5-inch figure of the popular character from the Transformers movies and TV shows. It comes with a variety of weapons and accessories.	19.99	14.99	Transformers	\N	\N	\N	Figures	\N	\N
585	\N	\N	PJ Masks Super Moon Adventure Vehicle	The PJ Masks Super Moon Adventure Vehicle is a playset based on the popular TV show. It comes with a variety of features, including a working winch, a zip line, and a secret hideout.	49.99	39.99	PJ Masks	\N	\N	\N	Playsets	\N	\N
586	\N	\N	Crayola Ultimate Crayon Collection	The Crayola Ultimate Crayon Collection is a set of 150 crayons in a variety of colors. It comes with a carrying case and a sharpener.	29.99	24.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
587	\N	\N	Melissa & Doug Wooden Activity Table	The Melissa & Doug Wooden Activity Table is a sturdy wooden table with a variety of activities, including a sandpit, a water table, and a chalkboard.	149.99	119.99	Melissa & Doug	\N	\N	\N	Activity Tables	\N	\N
588	\N	\N	VTech Sit-to-Stand Learning Walker	The VTech Sit-to-Stand Learning Walker is a walker that helps toddlers learn to walk and talk. It has a variety of features, including a light-up piano, a shape sorter, and a removable activity tray.	59.99	49.99	VTech	\N	\N	\N	Learning Toys	\N	\N
589	\N	\N	LeapFrog My Pal Scout	The LeapFrog My Pal Scout is a plush interactive toy that teaches toddlers about letters, numbers, and colors. It has a variety of features, including a light-up belly, a sing-along microphone, and a variety of learning games.	29.99	24.99	LeapFrog	\N	\N	\N	Learning Toys	\N	\N
590	\N	\N	Fisher-Price Little People Farm	The Fisher-Price Little People Farm is a playset that introduces toddlers to farm animals and life on the farm. It has a variety of features, including a barn, a tractor, and a variety of animal figures.	49.99	39.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
591	\N	\N	MEGA Bloks First Builders Big Building Bag	The MEGA Bloks First Builders Big Building Bag is a set of 80 large building blocks in a variety of colors and shapes. It is perfect for toddlers who are just learning to build.	19.99	14.99	MEGA Bloks	\N	\N	\N	Building Toys	\N	\N
592	\N	\N	Playskool Sit 'n Spin Classic	The Playskool Sit 'n Spin Classic is a classic toy that has been enjoyed by generations of children. It is a simple yet effective toy that helps toddlers develop their balance and coordination.	19.99	14.99	Playskool	\N	\N	\N	Activity Toys	\N	\N
593	\N	\N	Thomas & Friends TrackMaster Thomas and Percy Set	The Thomas & Friends TrackMaster Thomas and Percy Set is a train set that includes two engines, a track layout, and a variety of accessories. It is perfect for toddlers who love trains.	49.99	39.99	Thomas & Friends	\N	\N	\N	Train Sets	\N	\N
594	\N	\N	Playmobil 1.2.3 Aqua Water Fun	The Playmobil 1.2.3 Aqua Water Fun playset is a water-themed playset that is perfect for toddlers. It includes a variety of features, including a water slide, a boat, and a variety of animals.	29.99	24.99	Playmobil	\N	\N	\N	Playsets	\N	\N
595	\N	\N	Manhattan Toy Winkel Rattle & Sensory Teether Toy	The Manhattan Toy Winkel Rattle & Sensory Teether Toy is a multi-sensory toy that is perfect for babies and toddlers. It has a variety of features, including a rattle, a teether, and a variety of textures.	14.99	11.99	Manhattan Toy	\N	\N	\N	Sensory Toys	\N	\N
596	\N	\N	Sassy Developmental Bumpy Ball	The Sassy Developmental Bumpy Ball is a textured ball that is perfect for babies and toddlers. It helps develop fine motor skills and sensory awareness.	9.99	7.99	Sassy	\N	\N	\N	Sensory Toys	\N	\N
597	\N	\N	Skip Hop Explore & More 3-in-1 Activity Center	The Skip Hop Explore & More 3-in-1 Activity Center is a versatile play center that can be used as a jumper, a table, or a playmat. It has a variety of features, including a light-up piano, a shape sorter, and a variety of toys.	99.99	79.99	Skip Hop	\N	\N	\N	Activity Centers	\N	\N
598	\N	\N	Baby Einstein Sea Dreams Soother	The Baby Einstein Sea Dreams Soother is a musical soother that helps babies fall asleep. It has a variety of features, including a nightlight, a projector, and a variety of soothing sounds.	29.99	24.99	Baby Einstein	\N	\N	\N	Soothers	\N	\N
599	\N	\N	Infantino Prop-A-pillar Tummy Time & Seated Support	The Infantino Prop-A-pillar Tummy Time & Seated Support is a supportive pillow that helps babies develop their neck and back muscles. It can be used for tummy time or as a seated support.	19.99	14.99	Infantino	\N	\N	\N	Support Pillows	\N	\N
600	\N	\N	OXO Tot Twist Top Snack Cups	The OXO Tot Twist Top Snack Cups are a set of two snack cups with twist-top lids. They are perfect for storing snacks on the go.	9.99	7.99	OXO	\N	\N	\N	Feeding Accessories	\N	\N
601	\N	\N	Munchkin Miracle 360 Sippy Cup	The Munchkin Miracle 360 Sippy Cup is a sippy cup that allows toddlers to drink from any angle. It has a spill-proof design and is easy to clean.	9.99	7.99	Munchkin	\N	\N	\N	Sippy Cups	\N	\N
602	\N	\N	Tommee Tippee Closer to Nature Bottles	The Tommee Tippee Closer to Nature Bottles are a set of four bottles that are designed to mimic the natural shape and feel of a mother's breast. They have a slow-flow nipple and are easy for babies to latch onto.	19.99	14.99	Tommee Tippee	\N	\N	\N	Bottles	\N	\N
603	\N	\N	aden + anais Classic Swaddle Blankets	The aden + anais Classic Swaddle Blankets are a set of four swaddle blankets made from soft muslin cotton. They are perfect for swaddling babies and can also be used as a nursing cover or a stroller blanket.	49.99	39.99	aden + anais	\N	\N	\N	Baby Blankets	\N	\N
604	\N	\N	Ergobaby Embrace Baby Carrier	The Ergobaby Embrace Baby Carrier is a soft and comfortable baby carrier that is perfect for newborns. It has a variety of features, including a padded shoulder strap and a腰部支撑.	149.99	119.99	Ergobaby	\N	\N	\N	Baby Carriers	\N	\N
605	\N	\N	BabyBjorn Bouncer Bliss	The BabyBjorn Bouncer Bliss is a bouncer that rocks babies gently back and forth. It has a variety of features, including a three-position recline and a removable toy bar.	199.99	149.99	BabyBjorn	\N	\N	\N	Baby Bouncers	\N	\N
606	\N	\N	4moms mamaRoo 4 Infant Seat	The 4moms mamaRoo 4 Infant Seat is a swing that mimics the natural motions of a parent. It has a variety of features, including five different speeds and four different motions.	299.99	249.99	4moms	\N	\N	\N	Baby Swings	\N	\N
607	\N	\N	Graco Pack 'n Play Playard	The Graco Pack 'n Play Playard is a portable playard that is perfect for travel. It has a variety of features, including a changing table, a bassinet, and a playard.	99.99	79.99	Graco	\N	\N	\N	Playards	\N	\N
608	\N	\N	Chicco Bravo LE Travel System	The Chicco Bravo LE Travel System is a travel system that includes a stroller, a car seat, and a base. It is perfect for parents who are on the go.	299.99	249.99	Chicco	\N	\N	\N	Travel Systems	\N	\N
609	\N	\N	Nerf N-Strike Elite HyperFire Blaster	Fully automatic blaster with rotating barrel that holds 25 darts	24.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
610	\N	\N	LEGO Star Wars The Mandalorian's Razor Crest Building Kit	Buildable model of the Mandalorian's spacecraft	129.99	99.99	LEGO	\N	\N	\N	Building Toys	\N	\N
611	\N	\N	Barbie Dreamhouse Dollhouse	Three-story dollhouse with working elevator and multiple rooms	249.99	199.99	Barbie	\N	\N	\N	Dolls	\N	\N
612	\N	\N	Hot Wheels Ultimate Garage Track Set	Massive track set with over 140 pieces	89.99	59.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
613	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Ice cream truck playset with over 25 accessories	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
614	\N	\N	Crayola Washable Kids Paint Set	Set of 12 washable paint colors	14.99	9.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
615	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Magnetic doll with over 30 mix-and-match clothing pieces	24.99	19.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
616	\N	\N	American Girl Truly Me Doll	18-inch doll with customizable features	115.00	89.99	American Girl	\N	\N	\N	Dolls	\N	\N
617	\N	\N	Hatchimals CollEGGtibles Shimmering Seas Hatching Egg	Hatching egg with interactive toy inside	7.99	5.99	Hatchimals	\N	\N	\N	Toys for Girls	\N	\N
618	\N	\N	PAW Patrol Mighty Pups Super PAWs Skye Transforming Vehicle	Transforming vehicle with Skye figure	29.99	19.99	PAW Patrol	\N	\N	\N	Toy Vehicles	\N	\N
619	\N	\N	LEGO Technic Monster Jam Max-D Truck Building Kit	Buildable model of a Monster Jam truck	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
620	\N	\N	Nerf Fortnite BASR-L Blaster	Replica of the Fortnite BASR-L sniper rifle	29.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
621	\N	\N	Barbie Dreamtopia Magic Rainbow Unicorn	Unicorn doll with rainbow mane and tail	24.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
622	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm Playset	Monster truck playset with giant Megalodon	59.99	39.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
623	\N	\N	Play-Doh Modeling Compound 24-Pack	24-pack of Play-Doh modeling compound	19.99	14.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
624	\N	\N	Crayola Ultimate Washable Marker Set	Set of 100 washable markers	39.99	29.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
625	\N	\N	Melissa & Doug Wooden Activity Table	Activity table with four play surfaces	149.99	119.99	Melissa & Doug	\N	\N	\N	Activity Tables	\N	\N
626	\N	\N	Our Generation Regular Sized Doll - Joss	18-inch doll with realistic features	34.99	24.99	Our Generation	\N	\N	\N	Dolls	\N	\N
627	\N	\N	Hatchimals Surprise	Interactive toy that hatches into two unique creatures	79.99	59.99	Hatchimals	\N	\N	\N	Toys for Girls	\N	\N
628	\N	\N	PAW Patrol Sea Patrol Zuma's Hovercraft Vehicle	Hovercraft vehicle with Zuma figure	24.99	19.99	PAW Patrol	\N	\N	\N	Toy Vehicles	\N	\N
629	\N	\N	LEGO City Great Vehicles Race Car Transporter Building Kit	Buildable race car transporter truck	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
630	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	Replica of the Fortnite SP-L dart blaster	24.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
631	\N	\N	Barbie Chelsea Travel Doll and Playset	Chelsea doll with travel accessories	14.99	9.99	Barbie	\N	\N	\N	Dolls	\N	\N
632	\N	\N	Hot Wheels City Ultimate Garage Playset	Massive garage playset with over 140 pieces	149.99	99.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
633	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Cone Maker Playset	Ice cream cone maker playset with over 20 accessories	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
634	\N	\N	Crayola Super Tips Washable Markers	Set of 50 washable markers with super tips	24.99	19.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
635	\N	\N	Melissa & Doug Wooden Shape Sorter Clock	Shape sorter clock with 12 different shapes	29.99	19.99	Melissa & Doug	\N	\N	\N	Activity Tables	\N	\N
636	\N	\N	Our Generation Deluxe Horse and Stable	Horse and stable playset with over 30 accessories	149.99	99.99	Our Generation	\N	\N	\N	Playsets	\N	\N
637	\N	\N	Hatchimals Pixies Crystal Flyers Starlight Sprite	Interactive pixie toy that flies	14.99	9.99	Hatchimals	\N	\N	\N	Toys for Girls	\N	\N
638	\N	\N	PAW Patrol Mighty Pups Super PAWs Chase Transforming Vehicle	Transforming vehicle with Chase figure	29.99	19.99	PAW Patrol	\N	\N	\N	Toy Vehicles	\N	\N
639	\N	\N	LEGO Friends Heartlake City Park Playground Building Kit	Buildable playground scene	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
640	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	Replica of the Fortnite AR-L dart blaster	29.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
641	\N	\N	Barbie Dreamtopia Chelsea Mermaid Doll	Chelsea doll as a mermaid	14.99	9.99	Barbie	\N	\N	\N	Dolls	\N	\N
642	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm Remote Control Truck	Remote control Megalodon monster truck	79.99	59.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
643	\N	\N	Play-Doh Modeling Compound 36-Pack	36-pack of Play-Doh modeling compound	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
644	\N	\N	Crayola Super Washable Washable Markers	Set of 12 super washable markers	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
645	\N	\N	Buzz Lightyear Action Figure	Laser beam shooter, wings that extend, realistic lights and sounds	19.99	14.99	Disney	\N	\N	\N	Action Figures	\N	\N
646	\N	\N	Barbie Dreamhouse	Three-story house with elevator, furniture, and accessories	99.99	74.99	Barbie	\N	\N	\N	Dolls and Playsets	\N	\N
647	\N	\N	Hot Wheels Race Track Set	Track with curves, loops, and obstacles	39.99	29.99	Hot Wheels	\N	\N	\N	Vehicles and Tracks	\N	\N
648	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	Semi-automatic dart blaster with 10 darts	29.99	22.99	Nerf	\N	\N	\N	Blasters and Darts	\N	\N
649	\N	\N	LEGO Star Wars Millennium Falcon	Spaceship building set with over 1,300 pieces	149.99	119.99	LEGO	\N	\N	\N	Building Sets	\N	\N
650	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Ice cream truck play set with play dough and accessories	29.99	24.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
651	\N	\N	American Girl Doll	Historical or contemporary doll with accessories	119.99	94.99	American Girl	\N	\N	\N	Dolls and Playsets	\N	\N
652	\N	\N	Minecraft Steve Action Figure	Figure of Minecraft character Steve with sword and pickaxe	14.99	10.99	Minecraft	\N	\N	\N	Action Figures	\N	\N
653	\N	\N	Hatchimals Pixies Crystal Flyers Rainbow Glitter Fairy	Interactive flying fairy with lights and sounds	19.99	14.99	Hatchimals	\N	\N	\N	Electronic Toys	\N	\N
654	\N	\N	LOL Surprise! OMG Dance Doll with 20 Surprises	Fashion doll with 20 different accessories	29.99	24.99	LOL Surprise!	\N	\N	\N	Dolls and Playsets	\N	\N
655	\N	\N	Funko Pop! Harry Potter Hermione Granger Vinyl Figure	Collectible vinyl figure of Hermione Granger	14.99	10.99	Funko Pop!	\N	\N	\N	Collectibles	\N	\N
656	\N	\N	Squishmallows 12-Inch Plush Toy	Soft and huggable plush toy in various characters	19.99	14.99	Squishmallows	\N	\N	\N	Stuffed Animals	\N	\N
657	\N	\N	Beyblade Burst Surge Speedstorm Starter Pack	Beyblade top and launcher	14.99	10.99	Beyblade	\N	\N	\N	Toys for Boys	\N	\N
658	\N	\N	Paw Patrol Chase Transforming Vehicle	Chase police cruiser that transforms into a robot	19.99	14.99	Paw Patrol	\N	\N	\N	Vehicles and Tracks	\N	\N
659	\N	\N	Unicorn Slime Kit	Set for making and customizing unicorn slime	14.99	10.99	Elmer's	\N	\N	\N	Arts and Crafts	\N	\N
660	\N	\N	Nintendo Switch Lite	Handheld video game console	199.99	174.99	Nintendo	\N	\N	\N	Video Games	\N	\N
661	\N	\N	Roblox Jailbreak Playset	Set with Roblox jail, figures, and accessories	29.99	24.99	Roblox	\N	\N	\N	Playsets	\N	\N
662	\N	\N	Minecraft Dungeons Hero Edition	Video game with unique content and additional items	39.99	29.99	Minecraft	\N	\N	\N	Video Games	\N	\N
663	\N	\N	Crayola Washable Sidewalk Chalk	Set of 64 colorful sidewalk chalk sticks	9.99	7.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
664	\N	\N	Playmobil Ghostbusters Firehouse Headquarters	Ghostbusters fire station play set with figures and accessories	79.99	59.99	Playmobil	\N	\N	\N	Playsets	\N	\N
665	\N	\N	Nerf Fortnite BASR-L Blaster with Scope	Bolt-action dart blaster with scope	49.99	39.99	Nerf	\N	\N	\N	Blasters and Darts	\N	\N
980	\N	\N	Building Blocks	Set of 100 colorful building blocks	14.99	11.99	Mega Bloks	\N	\N	\N	Building	\N	\N
666	\N	\N	LEGO Minecraft The Pig House	Pig house building set with Minecraft characters	29.99	24.99	LEGO	\N	\N	\N	Building Sets	\N	\N
667	\N	\N	Barbie Color Reveal Mermaid Doll	Barbie mermaid doll that changes color in water	19.99	14.99	Barbie	\N	\N	\N	Dolls and Playsets	\N	\N
668	\N	\N	Hot Wheels Monster Trucks Demolition Doubles	Two-pack of monster truck toys	14.99	10.99	Hot Wheels	\N	\N	\N	Vehicles and Tracks	\N	\N
669	\N	\N	Melissa & Doug Doctor Play Set	Pretend play set with doctor tools and accessories	29.99	24.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
670	\N	\N	Play-Doh Super Color Pack	Assortment of 20 Play-Doh colors	19.99	14.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
671	\N	\N	Star Wars The Child Animatronic Edition	Interactive plush toy of Baby Yoda	49.99	39.99	Hasbro	\N	\N	\N	Electronic Toys	\N	\N
672	\N	\N	Pokémon Pikachu Plush	Plush toy of Pikachu	19.99	14.99	Pokémon	\N	\N	\N	Stuffed Animals	\N	\N
673	\N	\N	Beyblade Burst QuadDrive Battle Set Stadium	Battle stadium for Beyblade tops	29.99	24.99	Beyblade	\N	\N	\N	Toys for Boys	\N	\N
674	\N	\N	Nerf Ultra One Motorized Blaster with 25 Darts	Motorized dart blaster with 25 Ultra darts	49.99	39.99	Nerf	\N	\N	\N	Blasters and Darts	\N	\N
675	\N	\N	Crayola My First Washable Crayons	Set of 8 crayons for toddlers	9.99	7.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
676	\N	\N	LEGO Duplo Disney Cars Mater's Junkyard	Mater's junkyard building set with Cars characters	29.99	24.99	LEGO	\N	\N	\N	Building Sets	\N	\N
677	\N	\N	Hot Wheels Ultimate Garage Playset	Multi-level garage play set with cars and accessories	99.99	74.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
678	\N	\N	Melissa & Doug Puppet Theater	Wooden puppet theater with four finger puppets	39.99	29.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
679	\N	\N	Playmobil Dragons DreamWorks Dragons Toothless	Toothless dragon figure from DreamWorks Dragons	19.99	14.99	Playmobil	\N	\N	\N	Stuffed Animals	\N	\N
680	\N	\N	Nerf Fortnite TS-R Blaster	Semi-automatic dart blaster with 10 darts	29.99	22.99	Nerf	\N	\N	\N	Blasters and Darts	\N	\N
681	\N	\N	Lego Star Wars: The Razor Crest	Recreate scenes from the Star Wars: The Mandalorian TV series with this detailed, brick-built model of The Razor Crest.	149.99	119.99	LEGO	\N	\N	\N	Building Toys	\N	\N
682	\N	\N	LOL Surprise! OMG Remix Super Surprise	Unbox 70+ surprises with the LOL Surprise! OMG Remix Super Surprise.	109.99	89.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
683	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Make and serve pretend ice cream with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset.	29.99	19.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
684	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm RC Monster Truck	Take control of the giant Megalodon Monster Truck with the Hot Wheels Monster Trucks Live Megalodon Storm RC Monster Truck.	79.99	59.99	Hot Wheels	\N	\N	\N	Remote Control Vehicles	\N	\N
685	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	Fire foam darts up to 90 feet with the Nerf Fortnite SP-L Elite Dart Blaster.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
686	\N	\N	Minecraft Dungeons Hero Edition	Embark on an epic adventure with the Minecraft Dungeons Hero Edition.	29.99	19.99	Minecraft	\N	\N	\N	Video Games	\N	\N
687	\N	\N	Barbie Dreamhouse Adventures	Build, design, and decorate your own Barbie dreamhouse with the Barbie Dreamhouse Adventures app.	14.99	9.99	Barbie	\N	\N	\N	Dolls	\N	\N
688	\N	\N	Hot Wheels Criss Cross Crash Track Set	Race and crash cars on the Hot Wheels Criss Cross Crash Track Set.	49.99	39.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
689	\N	\N	Play-Doh Modeling Compound 24-Pack	Create and shape whatever you can imagine with the Play-Doh Modeling Compound 24-Pack.	14.99	9.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
690	\N	\N	Nintendo Switch Lite	Play your favorite Nintendo Switch games on the go with the Nintendo Switch Lite.	199.99	179.99	Nintendo	\N	\N	\N	Video Game Consoles	\N	\N
691	\N	\N	LOL Surprise! OMG House of Surprises	Unbox 85+ surprises and create your own LOL Surprise! world with the LOL Surprise! OMG House of Surprises.	109.99	89.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
692	\N	\N	LEGO Minecraft The Nether Bastion	Build and explore the Nether Bastion from the Minecraft video game with the LEGO Minecraft The Nether Bastion set.	59.99	49.99	LEGO	\N	\N	\N	Building Toys	\N	\N
693	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	Fire foam darts up to 100 feet with the Nerf Fortnite AR-L Elite Dart Blaster.	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
694	\N	\N	Barbie Fashionistas Doll	Express your own unique style with the Barbie Fashionistas Doll.	9.99	7.99	Barbie	\N	\N	\N	Dolls	\N	\N
695	\N	\N	Hot Wheels Monster Trucks Race Ace Monster Truck	Crush the competition with the Hot Wheels Monster Trucks Race Ace Monster Truck.	29.99	19.99	Hot Wheels	\N	\N	\N	Remote Control Vehicles	\N	\N
696	\N	\N	Play-Doh Kitchen Creations Ultimate Oven Playset	Bake and decorate pretend treats with the Play-Doh Kitchen Creations Ultimate Oven Playset.	29.99	19.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
697	\N	\N	Nintendo Switch Pro Controller	Enhance your gaming experience with the Nintendo Switch Pro Controller.	69.99	59.99	Nintendo	\N	\N	\N	Video Game Accessories	\N	\N
698	\N	\N	LOL Surprise! OMG Remix 4-Pack Fashion Dolls	Unbox 4 fabulous fashion dolls with the LOL Surprise! OMG Remix 4-Pack Fashion Dolls.	59.99	49.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
699	\N	\N	LEGO Harry Potter Hogwarts Express	Recreate iconic scenes from the Harry Potter movies with the LEGO Harry Potter Hogwarts Express.	79.99	69.99	LEGO	\N	\N	\N	Building Toys	\N	\N
700	\N	\N	Nerf Fortnite BASR-L Elite Dart Blaster	Take aim and fire with the Nerf Fortnite BASR-L Elite Dart Blaster.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
701	\N	\N	Barbie Dreamtopia Mermaid Doll	Dive into a world of imagination with the Barbie Dreamtopia Mermaid Doll.	14.99	9.99	Barbie	\N	\N	\N	Dolls	\N	\N
702	\N	\N	Hot Wheels Monster Trucks Mohawk Warrior Monster Truck	Charge into battle with the Hot Wheels Monster Trucks Mohawk Warrior Monster Truck.	29.99	19.99	Hot Wheels	\N	\N	\N	Remote Control Vehicles	\N	\N
703	\N	\N	Play-Doh Modeling Compound 10-Pack	Create and shape whatever you can imagine with the Play-Doh Modeling Compound 10-Pack.	9.99	4.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
704	\N	\N	Nintendo Switch Lite Carrying Case	Protect your Nintendo Switch Lite with the Nintendo Switch Lite Carrying Case.	19.99	14.99	Nintendo	\N	\N	\N	Video Game Accessories	\N	\N
705	\N	\N	LOL Surprise! OMG Remix Super Surprise Light-Up Doll	Unbox the ultimate unboxing experience with the LOL Surprise! OMG Remix Super Surprise Light-Up Doll.	59.99	49.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
706	\N	\N	LEGO Star Wars Mandalorian Starfighter	Build and fly the Mandalorian Starfighter from the Star Wars: The Mandalorian TV series with the LEGO Star Wars Mandalorian Starfighter.	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
707	\N	\N	Nerf Fortnite Pump SG Elite Dart Blaster	Blast into action with the Nerf Fortnite Pump SG Elite Dart Blaster.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
708	\N	\N	Barbie Extra Doll #1	Express your own unique style with the Barbie Extra Doll #1.	9.99	7.99	Barbie	\N	\N	\N	Dolls	\N	\N
709	\N	\N	Hot Wheels Criss Cross Crash Track Set Expansion Pack	Expand your Hot Wheels Criss Cross Crash Track Set with the Hot Wheels Criss Cross Crash Track Set Expansion Pack.	19.99	14.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
710	\N	\N	Play-Doh Kitchen Creations Ultimate Burger Playset	Create and customize your own pretend burgers with the Play-Doh Kitchen Creations Ultimate Burger Playset.	29.99	19.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
711	\N	\N	Nintendo Switch Online Family Membership	Play online with up to 8 family members with the Nintendo Switch Online Family Membership.	34.99	29.99	Nintendo	\N	\N	\N	Video Game Subscriptions	\N	\N
712	\N	\N	LOL Surprise! OMG Remix 2-Pack Fashion Dolls	Unbox 2 fabulous fashion dolls with the LOL Surprise! OMG Remix 2-Pack Fashion Dolls.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
713	\N	\N	LEGO Super Mario Adventures with Mario Starter Course	Start your LEGO Super Mario adventure with the LEGO Super Mario Adventures with Mario Starter Course.	59.99	49.99	LEGO	\N	\N	\N	Building Toys	\N	\N
714	\N	\N	Nerf Fortnite SMG-E Elite Dart Blaster	Fire foam darts up to 75 feet with the Nerf Fortnite SMG-E Elite Dart Blaster.	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
715	\N	\N	Barbie Dreamhouse	Create your own dream world with the Barbie Dreamhouse.	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
716	\N	\N	Mega Bloks Colossal Castle	Build and conquer with the Mega Bloks Colossal Castle! This massive castle playset features over 900 blocks, including special shapes like arches and pillars. Kids can create their own medieval adventures with the included knights, horses, and other accessories.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
717	\N	\N	Barbie Dreamhouse	Welcome to the Barbie Dreamhouse, the ultimate dollhouse for imaginative play! This three-story house features 10 rooms, a working elevator, a pool, and over 70 accessories. Kids can create endless stories with Barbie and her friends.	99.99	79.99	Barbie	\N	\N	\N	Dolls	\N	\N
718	\N	\N	Nerf Fortnite BASR-L	The Nerf Fortnite BASR-L is a bolt-action sniper rifle that fires Mega darts. It features a removable scope, adjustable stock, and a bipod for added stability. Kids can recreate their favorite Fortnite battles with this realistic blaster.	24.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
719	\N	\N	Minecraft Dungeons Hero Edition	Minecraft Dungeons Hero Edition includes the base game, the Jungle Awakens DLC, and the Creeping Winter DLC. Players can explore dungeons, battle mobs, and collect loot in this action-adventure game inspired by the popular Minecraft franchise.	29.99	24.99	Minecraft	\N	\N	\N	Video Games	\N	\N
720	\N	\N	LOL Surprise OMG Fierce Doll	LOL Surprise OMG Fierce Doll is the fierce and fabulous leader of the OMG Queens. She comes with 15 surprises, including a doll stand, accessories, and a collectible magazine. Kids can collect all four OMG Queens dolls to complete the set.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
721	\N	\N	Hot Wheels Monster Trucks Live Glow Racers	Hot Wheels Monster Trucks Live Glow Racers are remote-controlled monster trucks that glow in the dark. Kids can race and crash these trucks with up to four players at a time. The set includes two monster trucks, a track, and a launcher.	24.99	19.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
722	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	The Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset lets kids create and serve their own pretend ice cream treats. This playset features a working ice cream maker, molds, toppings, and a variety of Play-Doh colors.	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
723	\N	\N	Paw Patrol Lookout Tower	The Paw Patrol Lookout Tower is the headquarters for the Paw Patrol pups. This playset features a working elevator, a slide, a zip line, and a variety of other interactive features. Kids can recreate their favorite Paw Patrol rescues with this iconic playset.	49.99	39.99	Paw Patrol	\N	\N	\N	TV & Movie Toys	\N	\N
724	\N	\N	LEGO Star Wars The Mandalorian The Razor Crest	LEGO Star Wars The Mandalorian The Razor Crest is a detailed replica of the iconic ship from the hit Disney+ series. This set features over 1,000 pieces, including minifigures of The Mandalorian, Grogu, and Cara Dune. Kids can build and play with this amazing set to recreate their favorite Star Wars moments.	129.99	99.99	LEGO	\N	\N	\N	Building Toys	\N	\N
725	\N	\N	Crayola Ultimate Light Board Drawing Tablet	The Crayola Ultimate Light Board Drawing Tablet lets kids draw and create with light. This tablet features a large drawing surface, eight different light effects, and a variety of stencils and templates. Kids can trace, draw, and write on the tablet, and their creations will glow in the dark.	24.99	19.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
726	\N	\N	Nintendo Switch Lite	The Nintendo Switch Lite is a portable gaming console that lets kids play their favorite Nintendo Switch games on the go. This console is smaller and lighter than the original Nintendo Switch, making it perfect for taking on the road. Kids can enjoy games like Mario Kart 8 Deluxe, Animal Crossing: New Horizons, and Pokémon Sword and Shield on the Nintendo Switch Lite.	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
727	\N	\N	Nerf Ultra One	The Nerf Ultra One is the ultimate Nerf blaster. It features a high-capacity magazine, a long-range barrel, and a built-in scope. Kids can fire darts up to 120 feet with this powerful blaster.	49.99	39.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
728	\N	\N	Barbie Cutie Reveal Doll	Barbie Cutie Reveal Doll is a surprise doll that comes with 10 surprises. Kids can unbox the doll to reveal a soft, plush animal friend. The doll also comes with a variety of accessories, including clothing, shoes, and a hairbrush.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
729	\N	\N	Hot Wheels 5-Alarm Fire Station Playset	The Hot Wheels 5-Alarm Fire Station Playset is a massive playset that features a fire station, a fire truck, and over 20 accessories. Kids can race the fire truck down the track, put out fires, and rescue people with this exciting playset.	49.99	39.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
730	\N	\N	LEGO Minecraft The Nether Fortress	LEGO Minecraft The Nether Fortress is a detailed replica of the iconic structure from the popular Minecraft game. This set features over 300 pieces, including minifigures of Steve, Alex, and a ghast. Kids can build and play with this amazing set to recreate their favorite Minecraft adventures.	29.99	24.99	LEGO	\N	\N	\N	Building Toys	\N	\N
731	\N	\N	Swing	Baby swing with a soft seat and adjustable swing speed	50.00	40.00	Graco	\N	\N	\N	Baby Swings	\N	\N
732	\N	\N	Play-Doh Kitchen Creations Noodle Makin' Mania Playset	The Play-Doh Kitchen Creations Noodle Makin' Mania Playset lets kids create their own pretend noodle dishes. This playset features a noodle maker, molds, toppings, and a variety of Play-Doh colors. Kids can make spaghetti, macaroni, and other noodle shapes with this fun playset.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
758	\N	\N	Doll: Barbie Fashionista	Stylish Barbie doll with a variety of clothing and accessories, promoting self-expression and fashion appreciation	14.99	10.99	Barbie	\N	\N	\N	Dolls	\N	\N
733	\N	\N	Nerf Fortnite Pump SG	The Nerf Fortnite Pump SG is a shotgun-style blaster that fires Mega darts. It features a pump-action mechanism and a removable barrel. Kids can recreate their favorite Fortnite battles with this realistic blaster.	24.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
734	\N	\N	LOL Surprise OMG Queens Runway Diva Doll	LOL Surprise OMG Queens Runway Diva Doll is the fierce and fabulous queen of the fashion world. She comes with 15 surprises, including a doll stand, accessories, and a collectible magazine. Kids can collect all four OMG Queens dolls to complete the set.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
735	\N	\N	Hot Wheels Monster Trucks Mega Wrex	Hot Wheels Monster Trucks Mega Wrex is a massive monster truck with over-sized wheels and a roaring engine. This truck features a pull-back motor and can perform wheelies and other stunts. Kids can collect all of the Hot Wheels Monster Trucks to build their own monster truck fleet.	19.99	14.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
736	\N	\N	Play-Doh Kitchen Creations Sweet Shoppe Playset	The Play-Doh Kitchen Creations Sweet Shoppe Playset lets kids create their own pretend candy and desserts. This playset features a candy maker, molds, toppings, and a variety of Play-Doh colors. Kids can make gummy bears, lollipops, and other sweet treats with this fun playset.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
737	\N	\N	Paw Patrol Air Patroller	The Paw Patrol Air Patroller is a transforming jet that features a working cockpit, a cargo bay, and a launching pad. This vehicle comes with a Skye figure and a mini helicopter. Kids can recreate their favorite Paw Patrol rescues with this exciting playset.	49.99	39.99	Paw Patrol	\N	\N	\N	TV & Movie Toys	\N	\N
738	\N	\N	LEGO Harry Potter Hogwarts Clock Tower	LEGO Harry Potter Hogwarts Clock Tower is a detailed replica of the iconic tower from the Harry Potter movies. This set features over 900 pieces, including minifigures of Harry Potter, Ron Weasley, and Hermione Granger. Kids can build and play with this amazing set to recreate their favorite Harry Potter moments.	79.99	69.99	LEGO	\N	\N	\N	Building Toys	\N	\N
739	\N	\N	Crayola Washable Kids Paint	Crayola Washable Kids Paint is a non-toxic paint that is perfect for young artists. This paint is easy to clean up and comes in a variety of bright colors. Kids can use this paint to create their own masterpieces on paper, canvas, or other surfaces.	4.99	3.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
740	\N	\N	Nintendo Switch Joy-Con Controllers	Nintendo Switch Joy-Con Controllers are the versatile controllers for the Nintendo Switch console. These controllers can be used together or separately, and they feature a variety of motion controls and vibration feedback. Kids can use the Joy-Con controllers to play their favorite Nintendo Switch games.	79.99	69.99	Nintendo	\N	\N	\N	Video Games	\N	\N
741	\N	\N	Nerf Ultra Strike	The Nerf Ultra Strike is a high-powered blaster that fires Ultra darts. It features a rotating barrel, a built-in scope, and a variety of attachments. Kids can fire darts up to 120 feet with this powerful blaster.	29.99	24.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
742	\N	\N	Barbie Dreamhouse Camper	The Barbie Dreamhouse Camper is a 3-in-1 camper that features a kitchen, a bathroom, and a bedroom. This camper also comes with a variety of accessories, including a campfire, a picnic table, and a slide. Kids can recreate their favorite Barbie camping adventures with this fun playset.	49.99	39.99	Barbie	\N	\N	\N	Dolls	\N	\N
743	\N	\N	Hot Wheels Criss Cross Crash Track Set	The Hot Wheels Criss Cross Crash Track Set is a gravity-defying track set that features two criss-crossing loops. Kids can race their Hot Wheels cars through the loops and watch them crash into each other. This track set comes with two Hot Wheels cars and a launcher.	19.99	14.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
744	\N	\N	Play-Doh Modeling Compound 24-Pack	Play-Doh Modeling Compound 24-Pack is a set of 24 different colors of Play-Doh. This set is perfect for kids who love to create and play with Play-Doh. The non-toxic formula is safe for kids of all ages.	14.99	10.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
745	\N	\N	Nerf Fortnite SMG-E	The Nerf Fortnite SMG-E is a fully automatic blaster that fires Mega darts. It features a rotating barrel, a built-in scope, and a variety of attachments. Kids can recreate their favorite Fortnite battles with this realistic blaster.	29.99	24.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
746	\N	\N	LOL Surprise OMG Glamper Camper	LOL Surprise OMG Glamper Camper is the ultimate playset for LOL Surprise dolls. This camper features a pool, a slide, a dance floor, and over 50 surprises. Kids can collect all of the LOL Surprise OMG dolls to complete their set and create their own unique adventures.	199.99	149.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
747	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Kit	Hot Wheels Track Builder Unlimited Triple Loop Kit is a modular track set that lets kids create their own custom tracks. This kit comes with over 20 pieces, including track, loops, ramps, and connectors. Kids can use their imagination to build their own unique track layouts.	19.99	14.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
748	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Counter Playset	The Play-Doh Kitchen Creations Ultimate Ice Cream Counter Playset lets kids create their own pretend ice cream treats. This playset features a working ice cream maker, molds, toppings, and a variety of Play-Doh colors. Kids can make cones, sundaes, and other ice cream treats with this fun playset.	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
749	\N	\N	Drone with FPV Camera	Advanced drone with live video feed and easy controls, perfect for aerial exploration and photography	249.99	199.99	HyperX	\N	\N	\N	Electronics	\N	\N
750	\N	\N	Gaming Laptop	High-performance laptop designed for immersive gaming, featuring powerful graphics and a fast processor	999.99	899.99	Acer	\N	\N	\N	Electronics	\N	\N
751	\N	\N	Robot Building Kit	Educational and engaging kit to build and program your own robots, fostering creativity and STEM skills	79.99	59.99	LEGO	\N	\N	\N	Building Toys	\N	\N
752	\N	\N	Art Easel with Supplies	Complete art easel set with canvas, paints, brushes, and more, inspiring artistic expression	49.99	39.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
753	\N	\N	Science Experiment Kit	Hands-on science kit with experiments in chemistry, biology, and physics, igniting curiosity and scientific exploration	59.99	49.99	Thames & Kosmos	\N	\N	\N	Educational Toys	\N	\N
754	\N	\N	Board Game: Monopoly Junior	Classic board game adapted for younger players, teaching financial literacy and strategic thinking	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
755	\N	\N	Card Game: Magic: The Gathering	Fantasy card game with collectible cards and strategic gameplay, fostering imagination and critical thinking	14.99	11.99	Wizards of the Coast	\N	\N	\N	Card Games	\N	\N
756	\N	\N	Building Blocks: Mega Bloks	Colorful building blocks for creative constructions, developing fine motor skills and spatial reasoning	24.99	19.99	Mega	\N	\N	\N	Building Toys	\N	\N
757	\N	\N	Action Figure: Superman	Iconic superhero action figure with poseable joints and accessories, inspiring imaginative play and storytelling	19.99	14.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
759	\N	\N	Plushie: Squishmallow	Soft and cuddly plush toy with unique designs, providing comfort and companionship	19.99	16.99	Kellytoy	\N	\N	\N	Plushies	\N	\N
760	\N	\N	Remote Control Car: Traxxas Slash	High-speed remote control car with durable design and powerful motor, delivering thrilling racing action	299.99	249.99	Traxxas	\N	\N	\N	Remote Control Toys	\N	\N
761	\N	\N	Nerf Blaster: Fortnite BASR-L	Pump-action blaster inspired by the popular video game, featuring realistic details and long-range firing capabilities	24.99	19.99	Nerf	\N	\N	\N	Action Toys	\N	\N
762	\N	\N	Puzzle: Ravensburger Disney Princess	Ravensburger Disney Princess puzzle with 1000 pieces, challenging and rewarding, fostering patience and problem-solving skills	19.99	16.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
763	\N	\N	Book: Harry Potter and the Sorcerer's Stone	Enthralling fantasy novel that introduces the magical world of Harry Potter, fostering imagination and reading comprehension	14.99	11.99	J.K. Rowling	\N	\N	\N	Books	\N	\N
764	\N	\N	Craft Kit: Make Your Own Slime	Interactive kit to create custom slime with different colors, scents, and textures, promoting creativity and sensory exploration	12.99	9.99	Elmer's	\N	\N	\N	Craft Kits	\N	\N
765	\N	\N	Play Tent: Unicorn Castle	Enchanted play tent with unicorn design, providing a magical and imaginative play space	49.99	39.99	Melissa & Doug	\N	\N	\N	Play Tents	\N	\N
766	\N	\N	Musical Instrument: Keyboard	Portable keyboard with 61 keys and multiple sound effects, fostering musical creativity and expression	149.99	129.99	Yamaha	\N	\N	\N	Musical Instruments	\N	\N
767	\N	\N	Scooter: Razor A5 Lux	High-performance scooter with lightweight design and adjustable height, promoting active play and coordination	129.99	99.99	Razor	\N	\N	\N	Outdoor Toys	\N	\N
768	\N	\N	Dollhouse: KidKraft Willow Creek	Spacious dollhouse with multiple rooms, furniture, and accessories, encouraging imaginative play and social skills	299.99	249.99	KidKraft	\N	\N	\N	Dolls	\N	\N
769	\N	\N	Building Set: K'NEX Thrill Rides	Complex building set with motorized components to create thrilling roller coasters and other amusement park rides	99.99	79.99	K'NEX	\N	\N	\N	Building Toys	\N	\N
770	\N	\N	Video Game: Minecraft	Open-world sandbox video game where players can explore, create, and interact with the environment, fostering problem-solving and creativity	29.99	24.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
771	\N	\N	Board Game: Ticket to Ride	Strategy board game where players collect train cards and claim railway routes across North America, promoting geography and strategic thinking	49.99	39.99	Days of Wonder	\N	\N	\N	Board Games	\N	\N
772	\N	\N	Card Game: Uno	Classic card game where players match colors and numbers, promoting color recognition and basic math skills	7.99	5.99	Mattel	\N	\N	\N	Card Games	\N	\N
773	\N	\N	Building Blocks: LEGO City Police Station	Interactive police station playset with multiple rooms, vehicles, and minifigures, inspiring imaginative play and storytelling	79.99	59.99	LEGO	\N	\N	\N	Building Toys	\N	\N
774	\N	\N	Action Figure: Star Wars Darth Vader	Iconic Star Wars action figure with realistic details and light-up lightsaber, encouraging imaginative play and fandom	19.99	14.99	Hasbro	\N	\N	\N	Action Figures	\N	\N
775	\N	\N	Doll: American Girl Truly Me	Customizable doll with a variety of clothing and accessories, promoting self-expression and creativity	119.99	99.99	American Girl	\N	\N	\N	Dolls	\N	\N
776	\N	\N	Plushie: Build-A-Bear Workshop	Personalized teddy bear with a variety of clothing and accessories, fostering creativity and emotional attachment	29.99	24.99	Build-A-Bear Workshop	\N	\N	\N	Plushies	\N	\N
777	\N	\N	Remote Control Toy: Sphero Mini Activity Kit	Interactive robotic ball with programmable features and coding challenges, promoting STEM skills and creativity	79.99	59.99	Sphero	\N	\N	\N	Remote Control Toys	\N	\N
778	\N	\N	Nerf Blaster: Nerf Fortnite Pump SG	Compact shotgun-style Nerf blaster inspired by the video game, featuring pump-action firing and close-range power	19.99	16.99	Nerf	\N	\N	\N	Action Toys	\N	\N
779	\N	\N	Puzzle: Ravensburger Harry Potter Hogwarts	Ravensburger Harry Potter Hogwarts puzzle with 1000 pieces, featuring the iconic castle from the movie series, challenging and rewarding	19.99	16.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
780	\N	\N	Book: The Hunger Games	Dystopian novel that explores themes of survival, rebellion, and personal growth, fostering critical thinking and social awareness	12.99	9.99	Suzanne Collins	\N	\N	\N	Books	\N	\N
781	\N	\N	Craft Kit: Crayola Color Wonder Mess-Free Coloring	Mess-free coloring kit with special markers and paper that only show color when used together, preventing spills and stains	14.99	11.99	Crayola	\N	\N	\N	Craft Kits	\N	\N
782	\N	\N	Play Tent: Disney Princess Enchanted Playhouse	Magical play tent with Disney Princess designs, featuring a spacious interior and pop-up tunnel, encouraging imaginative play and social interaction	39.99	29.99	Disney	\N	\N	\N	Play Tents	\N	\N
783	\N	\N	Hot Wheels Extreme Stunts Set	Awesome set for extreme stunts with loopings and daring jumps.	49.99	39.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
784	\N	\N	Barbie Dreamhouse 3-Story Townhouse	Spacious townhouse with 3 floors, 8 rooms and multiple accessories.	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
785	\N	\N	Nerf Fortnite BASR-L Blaster	Realistic blaster inspired by the popular video game Fortnite.	49.99	34.99	Nerf	\N	\N	\N	Outdoor	\N	\N
786	\N	\N	LEGO Star Wars Millennium Falcon	Detailed model of the iconic spaceship from the Star Wars movies.	149.99	119.99	LEGO	\N	\N	\N	Construction	\N	\N
787	\N	\N	American Girl Doll and Accessories	18-inch doll with a variety of outfits and accessories.	129.99	99.99	American Girl	\N	\N	\N	Dolls	\N	\N
788	\N	\N	Razor E100 Electric Scooter	Compact and portable electric scooter for kids aged 8 and up.	199.99	149.99	Razor	\N	\N	\N	Outdoor	\N	\N
789	\N	\N	Hatchimals CollEGGtibles 24-Pack	Assortment of 24 cute and interactive Hatchimals in colorful eggs.	49.99	34.99	Hatchimals	\N	\N	\N	Collectibles	\N	\N
790	\N	\N	Nintendo Switch Lite Console	Portable gaming console with access to a wide range of Nintendo games.	199.99	179.99	Nintendo	\N	\N	\N	Electronics	\N	\N
791	\N	\N	Beyblade Burst Pro Series Stadium	High-performance stadium for intense Beyblade battles.	49.99	39.99	Beyblade	\N	\N	\N	Toys	\N	\N
792	\N	\N	Car Seat	Car seat for infants and toddlers	60.00	48.00	Chicco	\N	\N	\N	Car Seats	\N	\N
793	\N	\N	Melissa & Doug Wooden Grocery Store	Interactive playset with a variety of wooden grocery items.	99.99	79.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
794	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Playful ice cream truck playset with molds, extruder and accessories.	29.99	19.99	Play-Doh	\N	\N	\N	Creative Play	\N	\N
795	\N	\N	Minecraft Dungeons Hero Edition	Action-adventure game set in the Minecraft universe.	29.99	19.99	Minecraft	\N	\N	\N	Video Games	\N	\N
796	\N	\N	LOL Surprise! OMG House of Surprises	Multi-level dollhouse with exclusive dolls, furniture and accessories.	199.99	149.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
797	\N	\N	Nerf Elite 2.0 Phoenix CS-6 Blaster	Powerful blaster with 6-dart capacity and slam-fire action.	29.99	19.99	Nerf	\N	\N	\N	Outdoor	\N	\N
798	\N	\N	LEGO Friends Heartlake City Amusement Pier	Detailed amusement pier playset with rides, games and shops.	99.99	79.99	LEGO	\N	\N	\N	Construction	\N	\N
799	\N	\N	Barbie Color Reveal Doll & Accessories	Mystery doll with color-changing hair, outfits and accessories.	24.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
800	\N	\N	Hot Wheels Monster Trucks Bone Shaker	Giant monster truck with oversized wheels and realistic details.	19.99	14.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
801	\N	\N	PAW Patrol Air Patroller	Transforming playset with lights, sounds and a rotating propeller.	79.99	59.99	PAW Patrol	\N	\N	\N	Vehicles	\N	\N
802	\N	\N	UNO Flip! Card Game	Classic card game with a twist, featuring a double-sided deck.	9.99	6.99	UNO	\N	\N	\N	Card Games	\N	\N
803	\N	\N	Crayola Ultimate Crayons Collection	Assortment of 150 crayons in a variety of colors.	29.99	19.99	Crayola	\N	\N	\N	Creative Play	\N	\N
804	\N	\N	Play-Doh Kitchen Creations My First Kitchen	Interactive playset with tools, molds and accessories for pretend cooking.	19.99	14.99	Play-Doh	\N	\N	\N	Creative Play	\N	\N
805	\N	\N	Minecraft Dungeons Creeper Battle Figure	Authentic and detailed figure of the iconic Minecraft mob.	14.99	9.99	Minecraft	\N	\N	\N	Toys	\N	\N
806	\N	\N	Barbie Dream Closet	Portable closet with hanging rods, shelves and multiple accessories.	49.99	39.99	Barbie	\N	\N	\N	Dolls	\N	\N
807	\N	\N	Nerf Fortnite Pump-SG Shotgun	Pump-action shotgun inspired by the popular video game Fortnite.	29.99	19.99	Nerf	\N	\N	\N	Outdoor	\N	\N
808	\N	\N	LEGO City Fire Station	Realistic fire station playset with multiple levels, vehicles and accessories.	79.99	59.99	LEGO	\N	\N	\N	Construction	\N	\N
809	\N	\N	Hatchimals Pixies Crystal Flyers	Interactive flying pixies with lights, sounds and responsive wings.	14.99	9.99	Hatchimals	\N	\N	\N	Toys	\N	\N
810	\N	\N	PAW Patrol Chase's Police Cruiser	Authentic police cruiser playset with lights, sounds and a movable claw.	29.99	19.99	PAW Patrol	\N	\N	\N	Vehicles	\N	\N
811	\N	\N	Nerf Alpha Strike Stinger SD-1 Blaster	Compact and easy-to-use blaster with rotating barrel.	19.99	14.99	Nerf	\N	\N	\N	Outdoor	\N	\N
812	\N	\N	LEGO Super Mario Adventures with Luigi Starter Course	Interactive playset featuring Luigi, interactive bricks and challenges.	59.99	49.99	LEGO	\N	\N	\N	Construction	\N	\N
813	\N	\N	Barbie Estate Dreamhouse	Magnificent dollhouse with multiple rooms, furniture and accessories.	399.99	299.99	Barbie	\N	\N	\N	Dolls	\N	\N
814	\N	\N	Hot Wheels Monster Trucks Demolition Doubles	Set of 2 monster trucks with unique designs and giant wheels.	24.99	19.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
815	\N	\N	Nerf Fortnite TS-R	Assault rifle with burst-fire action and included banana clip.	39.99	29.99	Nerf	\N	\N	\N	Outdoor	\N	\N
816	\N	\N	LEGO Star Wars The Child	Buildable model of the beloved character from The Mandalorian series.	19.99	14.99	LEGO	\N	\N	\N	Construction	\N	\N
817	\N	\N	PAW Patrol Lookout Tower	Interactive playset featuring the iconic lookout tower, vehicles and characters.	99.99	79.99	PAW Patrol	\N	\N	\N	Vehicles	\N	\N
818	\N	\N	Nintendo Switch Lite Bundle	Console bundle with carrying case, screen protector and game voucher.	249.99	219.99	Nintendo	\N	\N	\N	Electronics	\N	\N
819	\N	\N	Stunt Bike Extreme	Full-throttle racing action for boys and girls ages 13 and up!	199.99	149.99	Razor	\N	\N	\N	Bikes	\N	\N
820	\N	\N	Hoverboard Blast	The ultimate hoverboarding experience for kids ages 13 and up!	399.99	299.99	Swagtron	\N	\N	\N	Hoverboards	\N	\N
821	\N	\N	Nerf Rival Nemesis MXVII-10K	Fully automatic blaster with a 100-round capacity for kids ages 14 and up!	129.99	99.99	Nerf	\N	\N	\N	Blasters	\N	\N
822	\N	\N	Minecraft Dungeons Hero Edition	Explore the Minecraft world with friends in this action-packed adventure game for kids ages 10 and up!	49.99	39.99	Mojang	\N	\N	\N	Video Games	\N	\N
823	\N	\N	Roblox Robux Gift Card	Purchase Robux to enhance your Roblox experience for kids ages 13 and up!	25.00	25.00	Roblox	\N	\N	\N	Gift Cards	\N	\N
824	\N	\N	Barbie Dreamhouse Adventures	Create your own Barbie dreamhouse and play with your favorite characters for girls ages 13 and up!	149.99	99.99	Barbie	\N	\N	\N	Dolls	\N	\N
825	\N	\N	Hot Wheels Ultimate Garage	Multi-level garage with storage for over 140 Hot Wheels cars for boys ages 5 and up!	299.99	249.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
826	\N	\N	Minecraft Dungeons Hero Edition	Explore the Minecraft world with friends in this action-packed adventure game for kids ages 10 and up!	49.99	39.99	Mojang	\N	\N	\N	Video Games	\N	\N
827	\N	\N	Nerf Fortnite BASR-L	Pump-action blaster inspired by the popular Fortnite video game for kids ages 14 and up!	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
828	\N	\N	Nintendo Switch Lite	Play your favorite Nintendo Switch games on the go for kids ages 13 and up!	199.99	179.99	Nintendo	\N	\N	\N	Consoles	\N	\N
829	\N	\N	Roblox Robux Gift Card	Purchase Robux to enhance your Roblox experience for kids ages 13 and up!	50.00	50.00	Roblox	\N	\N	\N	Gift Cards	\N	\N
830	\N	\N	LOL Surprise OMG House of Surprises	Unbox 85+ surprises with this glamorous dollhouse for girls ages 13 and up!	199.99	149.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
831	\N	\N	Hot Wheels Monster Trucks Live Glow Party	Witness monster trucks perform gravity-defying stunts in a live show for boys and girls ages 5 and up!	49.99	39.99	Hot Wheels	\N	\N	\N	Events	\N	\N
832	\N	\N	Nintendo Switch Sports	Compete in a variety of sports with friends and family on the Nintendo Switch for kids ages 13 and up!	49.99	39.99	Nintendo	\N	\N	\N	Video Games	\N	\N
833	\N	\N	Nerf Fortnite HC-E	Semi-automatic blaster inspired by the popular Fortnite video game for kids ages 14 and up!	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
834	\N	\N	Minecraft Dungeons Hero Edition	Explore the Minecraft world with friends in this action-packed adventure game for kids ages 10 and up!	49.99	39.99	Mojang	\N	\N	\N	Video Games	\N	\N
835	\N	\N	Roblox Robux Gift Card	Purchase Robux to enhance your Roblox experience for kids ages 13 and up!	100.00	100.00	Roblox	\N	\N	\N	Gift Cards	\N	\N
836	\N	\N	Crayola Inspiration Art Case	Complete art set with over 140 pieces for kids ages 13 and up!	49.99	39.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
837	\N	\N	Hot Wheels Ultimate Garage	Multi-level garage with storage for over 140 Hot Wheels cars for boys ages 5 and up!	299.99	249.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
838	\N	\N	Minecraft Dungeons Hero Edition	Explore the Minecraft world with friends in this action-packed adventure game for kids ages 10 and up!	49.99	39.99	Mojang	\N	\N	\N	Video Games	\N	\N
839	\N	\N	Nerf Fortnite BASR-L	Pump-action blaster inspired by the popular Fortnite video game for kids ages 14 and up!	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
840	\N	\N	Nintendo Switch Lite	Play your favorite Nintendo Switch games on the go for kids ages 13 and up!	199.99	179.99	Nintendo	\N	\N	\N	Consoles	\N	\N
841	\N	\N	Roblox Robux Gift Card	Purchase Robux to enhance your Roblox experience for kids ages 13 and up!	50.00	50.00	Roblox	\N	\N	\N	Gift Cards	\N	\N
842	\N	\N	LOL Surprise OMG House of Surprises	Unbox 85+ surprises with this glamorous dollhouse for girls ages 13 and up!	199.99	149.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
843	\N	\N	Hot Wheels Monster Trucks Live Glow Party	Witness monster trucks perform gravity-defying stunts in a live show for boys and girls ages 5 and up!	49.99	39.99	Hot Wheels	\N	\N	\N	Events	\N	\N
844	\N	\N	Nintendo Switch Sports	Compete in a variety of sports with friends and family on the Nintendo Switch for kids ages 13 and up!	49.99	39.99	Nintendo	\N	\N	\N	Video Games	\N	\N
845	\N	\N	Nerf Fortnite HC-E	Semi-automatic blaster inspired by the popular Fortnite video game for kids ages 14 and up!	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
846	\N	\N	Minecraft Dungeons Hero Edition	Explore the Minecraft world with friends in this action-packed adventure game for kids ages 10 and up!	49.99	39.99	Mojang	\N	\N	\N	Video Games	\N	\N
847	\N	\N	Roblox Robux Gift Card	Purchase Robux to enhance your Roblox experience for kids ages 13 and up!	100.00	100.00	Roblox	\N	\N	\N	Gift Cards	\N	\N
848	\N	\N	Crayola Inspiration Art Case	Complete art set with over 140 pieces for kids ages 13 and up!	49.99	39.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
849	\N	\N	Hot Wheels Ultimate Garage	Multi-level garage with storage for over 140 Hot Wheels cars for boys ages 5 and up!	299.99	249.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
850	\N	\N	16-in-1 Solar Robot Kit	Build 16 Different Types of Robots. Runs on sun or battery. Great STEM Learning Experience	19.99	14.99	Thames & Kosmos	\N	\N	\N	Science & Nature	\N	\N
851	\N	\N	Unicorn Backpack for Girls	Unicorn Backpack with Sequins and Plush Horn. Adjustable Shoulder Straps and Roomy Compartments	24.99	19.99	Dreamseek	\N	\N	\N	Backpacks & Bags	\N	\N
852	\N	\N	Walkie Talkies for Kids	2-Way Walkie Talkies with Long Range and Clear Sound. Perfect for Outdoor Adventures	19.99	14.99	Retevis	\N	\N	\N	Electronics	\N	\N
853	\N	\N	Nerf Hyper Rush-40 Blaster	High-Capacity Hopper-Fed Blaster with 40-Dart Capacity and Rapid Fire Action	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
854	\N	\N	Slime Kit for Girls	Make Your Own Slime with 10 Colors of Glue, Glitter, Beads, and Scented Oils	19.99	14.99	Creativity for Kids	\N	\N	\N	Arts & Crafts	\N	\N
855	\N	\N	Stunt Scooter for Boys	Pro Scooter with 100mm Wheels, ABEC-7 Bearings, and BMX-Style Handlebars	79.99	59.99	Razor	\N	\N	\N	Ride-Ons	\N	\N
856	\N	\N	Barbie Dreamhouse	Multi-Level Dollhouse with 7 Rooms, Elevator, Pool, and Accessories	99.99	79.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
857	\N	\N	Hot Wheels Super Ultimate Garage Track Set	6-Level Garage with 142 Parking Spaces, Spiral Tracks, and Crash Zone	129.99	99.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
858	\N	\N	Build-a-Bear Workshop	Teddy Bear Stuffing Station with Clothes, Accessories, and Sound Effects	29.99	24.99	Build-A-Bear	\N	\N	\N	Stuffed Animals	\N	\N
859	\N	\N	LEGO Minecraft The Pig House	Minecraft-Themed Playset with Pig House, Pigsty, TNT Launcher, and Steve and Alex Minifigures	29.99	24.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
860	\N	\N	AirFort Inflatable Fort	Inflatable Play Fort with LED Lights and Glow-in-the-Dark Stars	39.99	29.99	AirFort	\N	\N	\N	Playhouses & Tents	\N	\N
861	\N	\N	Sphero Mini Activity Kit	Interactive Robot Ball with Coding App and STEM Challenges	49.99	39.99	Sphero	\N	\N	\N	Robotics	\N	\N
862	\N	\N	Hover Soccer Ball with LED Lights	Air-Powered Soccer Ball with Built-in LED Lights for Indoor and Outdoor Play	19.99	14.99	Hover Soccer	\N	\N	\N	Sports & Games	\N	\N
863	\N	\N	Kinetic Sand Castle Playset	Sensory Playset with 2 Pounds of Sand, Castle Molds, and Tools	19.99	14.99	Kinetic Sand	\N	\N	\N	Arts & Crafts	\N	\N
864	\N	\N	Nerf Fortnite Nerf Rival Prometheus MXVIII-20K Blaster	High-Capacity Blaster with 200-Round Hopper and Adjustable Stock	79.99	59.99	Nerf	\N	\N	\N	Blasters	\N	\N
865	\N	\N	Giant Teddy Bear	Oversized Teddy Bear Standing 6 Feet Tall. Super Soft and Cuddly	99.99	79.99	Teddy Mountain	\N	\N	\N	Stuffed Animals	\N	\N
866	\N	\N	Barbie Glam Convertible	Convertible Car with Working Headlights, Sound Effects, and Accessories	39.99	29.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
867	\N	\N	Melissa & Doug Magnetic Dress-Up Pretend Play Set	Wooden Magnetic Dress-Up Doll with 48 Clothing and Accessory Pieces	29.99	24.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
868	\N	\N	Play-Doh Kitchen Creations Ultimate Baking Playset	Play Kitchen with Mixer, Oven, Ice Cream Machine, and 20 Accessories	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
869	\N	\N	LOL Surprise OMG House of Surprises	3-Story Dollhouse with 8 Rooms, 80+ Surprises, and Exclusive Doll	109.99	89.99	LOL Surprise	\N	\N	\N	Dolls & Accessories	\N	\N
870	\N	\N	Pokémon TCG Sword & Shield Astral Radiance Elite Trainer Box	Expansion Pack with 10 Boosters, 1 Deck Box, 100 Energy Cards	49.99	39.99	Pokémon	\N	\N	\N	Trading Card Games	\N	\N
871	\N	\N	Minecraft Dungeons Hero Edition	Action-Adventure Game with Hero Pass, 2 DLC Packs, and Exclusive In-Game Items	29.99	24.99	Minecraft	\N	\N	\N	Video Games	\N	\N
872	\N	\N	LEGO Star Wars The Razor Crest Microfighter	Buildable Mini Star Wars Ship with Mandalorian and Grogu Minifigures	9.99	7.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
873	\N	\N	Hot Wheels Mario Kart Circuit Track Set	Mario-Themed Track Set with Rainbow Road, Goomba Hills, and Boo-Shaped Obstacles	49.99	39.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
874	\N	\N	Paw Patrol Mighty Pups Super Paws Lookout Tower Playset	3-Level Tower with Lights, Sounds, and 6 Transforming Vehicles	69.99	49.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
875	\N	\N	Fortnite Nerf Elite Victory Royale HC-E Blaster	Nerf Blaster with 6-Dart Rotating Barrel and Tactical Rails	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
876	\N	\N	AirBlasterz X-Shot Micro Turbo Fire	High-Performance Foam Dart Blaster with 5-Round Rotating Drum	19.99	14.99	X-Shot	\N	\N	\N	Blasters	\N	\N
877	\N	\N	Crayola Ultimate Light Board Drawing Tablet	Lighted Drawing Tablet with Markers, Paper, and Stencils	29.99	24.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
878	\N	\N	Barbie Color Reveal Mermaid Playset	Color-Changing Mermaid with Accessories and Play Pool	19.99	14.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
879	\N	\N	National Geographic Kids Volcano Science Kit	Build Your Own Erupting Volcano with Lava Slime and Excavation Tools	19.99	14.99	National Geographic Kids	\N	\N	\N	Science & Nature	\N	\N
880	\N	\N	Osmo Coding Awbie STEM Kit	Coding Kit with Physical Coding Blocks and Games	59.99	49.99	Osmo	\N	\N	\N	Robotics	\N	\N
881	\N	\N	My Little Pony Rainbow Dash Plush	My Little Pony Rainbow Dash Plush toy is a great gift for any fan of the My Little Pony franchise. It is made of soft, cuddly material and features Rainbow Dash's signature rainbow mane and tail. The plush toy is also poseable, so kids can create their own adventures with Rainbow Dash.	19.99	14.99	My Little Pony	\N	\N	\N	Plush Toys	\N	\N
882	\N	\N	Paw Patrol Chase Plush	Paw Patrol Chase Plush toy is a great gift for any fan of the Paw Patrol franchise. It is made of soft, cuddly material and features Chase's signature police uniform and pup pack. The plush toy is also poseable, so kids can create their own adventures with Chase.	19.99	14.99	Paw Patrol	\N	\N	\N	Plush Toys	\N	\N
883	\N	\N	Hot Wheels Monster Trucks 5-Alarm	Hot Wheels Monster Trucks 5-Alarm is a great gift for any fan of monster trucks. It features a large, rugged design with oversized wheels and a pull-back motor. The truck is also decorated with realistic fire and rescue graphics.	14.99	9.99	Hot Wheels	\N	\N	\N	Monster Trucks	\N	\N
884	\N	\N	Barbie Dreamhouse	Barbie Dreamhouse is a great gift for any fan of Barbie dolls. It features three stories, eight rooms, and over 70 accessories. The house also has a working elevator, a pool, and a slide.	199.99	149.99	Barbie	\N	\N	\N	Playsets	\N	\N
885	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset is a great gift for any fan of Play-Doh. It features a large, colorful ice cream truck with a working ice cream maker, a cash register, and a freezer. The playset also comes with a variety of Play-Doh colors and accessories.	29.99	19.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
886	\N	\N	LEGO Star Wars Millennium Falcon	LEGO Star Wars Millennium Falcon is a great gift for any fan of Star Wars. It features over 7,500 pieces and is one of the largest LEGO sets ever made. The set includes a detailed recreation of the Millennium Falcon, as well as minifigures of Han Solo, Luke Skywalker, Princess Leia, and Chewbacca.	799.99	599.99	LEGO	\N	\N	\N	Building Toys	\N	\N
887	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	Nerf Fortnite AR-L Elite Dart Blaster is a great gift for any fan of Fortnite. It features a motorized design that can fire up to 10 darts per second. The blaster also comes with a 20-dart clip and a removable stock.	29.99	19.99	Nerf	\N	\N	\N	Blasters	\N	\N
888	\N	\N	LOL Surprise! OMG House of Surprises	LOL Surprise! OMG House of Surprises is a great gift for any fan of LOL Surprise! dolls. It features four floors, six rooms, and over 80 surprises. The house also comes with exclusive LOL Surprise! dolls and accessories.	199.99	149.99	LOL Surprise!	\N	\N	\N	Playsets	\N	\N
889	\N	\N	Crayola Ultimate Crayon Collection	Crayola Ultimate Crayon Collection is a great gift for any fan of crayons. It features over 150 crayons in a variety of colors and styles. The crayons are also non-toxic and washable.	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
890	\N	\N	Melissa & Doug Wooden Activity Table	Melissa & Doug Wooden Activity Table is a great gift for toddlers. It features a double-sided design with a variety of activities, including a chalkboard, a magnetic board, and a bead maze. The table also comes with a variety of wooden blocks and shapes.	49.99	34.99	Melissa & Doug	\N	\N	\N	Activity Tables	\N	\N
891	\N	\N	LeapFrog My Pal Scout	LeapFrog My Pal Scout is a great gift for toddlers. It is an interactive plush toy that teaches kids about letters, numbers, and shapes. Scout also sings songs and tells stories.	29.99	19.99	LeapFrog	\N	\N	\N	Plush Toys	\N	\N
892	\N	\N	VTech Sit-to-Stand Learning Walker	VTech Sit-to-Stand Learning Walker is a great gift for babies. It helps babies learn to walk and talk. The walker also features a variety of activities, including a piano, a shape sorter, and a bead maze.	39.99	29.99	VTech	\N	\N	\N	Activity Walkers	\N	\N
893	\N	\N	Fisher-Price Little People Farm	Fisher-Price Little People Farm is a great gift for toddlers. It features a variety of farm animals, a barn, and a tractor. The farm also comes with a variety of Little People figures.	29.99	19.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
894	\N	\N	Mega Bloks First Builders Big Building Bag	Mega Bloks First Builders Big Building Bag is a great gift for toddlers. It features over 80 large, colorful blocks. The blocks are also easy to grip and stack.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
895	\N	\N	Play-Doh Kitchen Creations Magical Oven	Play-Doh Kitchen Creations Magical Oven is a great gift for toddlers. It features a working oven that can bake Play-Doh creations. The oven also comes with a variety of Play-Doh colors and accessories.	19.99	14.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
896	\N	\N	Crayola Washable Sidewalk Chalk	Crayola Washable Sidewalk Chalk is a great gift for kids. It features 12 bright and colorful chalk sticks. The chalk is also washable and non-toxic.	4.99	2.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
897	\N	\N	Melissa & Doug Wooden Bead Maze	Melissa & Doug Wooden Bead Maze is a great gift for toddlers. It features a variety of colorful beads and a sturdy wooden frame. The bead maze also helps toddlers develop fine motor skills.	19.99	14.99	Melissa & Doug	\N	\N	\N	Activity Toys	\N	\N
898	\N	\N	VTech Pop-a-Balls Push and Pop Bulldozer	VTech Pop-a-Balls Push and Pop Bulldozer is a great gift for toddlers. It features a bulldozer with a variety of colorful balls. The bulldozer also helps toddlers develop hand-eye coordination and fine motor skills.	19.99	14.99	VTech	\N	\N	\N	Activity Toys	\N	\N
899	\N	\N	Fisher-Price Laugh & Learn Smart Stages Puppy	Fisher-Price Laugh & Learn Smart Stages Puppy is a great gift for babies. It features a variety of interactive buttons and sensors that teach babies about letters, numbers, and shapes. The puppy also sings songs and tells stories.	19.99	14.99	Fisher-Price	\N	\N	\N	Plush Toys	\N	\N
900	\N	\N	Mega Bloks First Builders Scooping Wagon	Mega Bloks First Builders Scooping Wagon is a great gift for toddlers. It features a wagon with a variety of colorful blocks. The wagon also helps toddlers develop fine motor skills and problem-solving skills.	14.99	9.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
901	\N	\N	Play-Doh Kitchen Creations Noodle Maker	Play-Doh Kitchen Creations Noodle Maker is a great gift for toddlers. It features a noodle maker that can create a variety of different noodle shapes. The noodle maker also comes with a variety of Play-Doh colors and accessories.	14.99	9.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
902	\N	\N	Crayola Washable Markers	Crayola Washable Markers are a great gift for kids. They feature 10 bright and colorful markers. The markers are also washable and non-toxic.	9.99	4.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
903	\N	\N	Melissa & Doug Wooden Alphabet Puzzle	Melissa & Doug Wooden Alphabet Puzzle is a great gift for toddlers. It features a sturdy wooden frame and 26 colorful wooden letters. The puzzle also helps toddlers develop letter recognition and problem-solving skills.	14.99	9.99	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
904	\N	\N	VTech Little Smart	VTech Little Smart is a great gift for babies. It features a variety of interactive buttons and sensors that teach babies about letters, numbers, and shapes. Little Smart also sings songs and tells stories.	14.99	9.99	VTech	\N	\N	\N	Plush Toys	\N	\N
905	\N	\N	Fisher-Price Little People Zoo Train	Fisher-Price Little People Zoo Train is a great gift for toddlers. It features a train with a variety of colorful animals. The train also helps toddlers develop fine motor skills and problem-solving skills.	19.99	14.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
978	\N	\N	Toy Car	Red toy car with working wheels and doors	10.99	7.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
906	\N	\N	Mega Bloks First Builders Deluxe Building Bag	Mega Bloks First Builders Deluxe Building Bag is a great gift for toddlers. It features over 150 large, colorful blocks. The blocks are also easy to grip and stack.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
907	\N	\N	Play-Doh Kitchen Creations Ice Cream Cone Maker	Play-Doh Kitchen Creations Ice Cream Cone Maker is a great gift for toddlers. It features an ice cream cone maker that can create a variety of different ice cream cone shapes. The ice cream cone maker also comes with a variety of Play-Doh colors and accessories.	14.99	9.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
908	\N	\N	Crayola Twistables Colored Pencils	Crayola Twistables Colored Pencils are a great gift for kids. They feature 12 bright and colorful colored pencils. The colored pencils are also pre-sharpened and never need sharpening.	9.99	4.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
909	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Melissa & Doug Wooden Magnetic Dress-Up Doll is a great gift for toddlers. It features a wooden doll with a variety of magnetic clothing pieces. The doll also helps toddlers develop fine motor skills and problem-solving skills.	19.99	14.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
910	\N	\N	VTech Sit-to-Stand Activity Center	VTech Sit-to-Stand Activity Center is a great gift for babies. It features a variety of interactive activities that help babies learn about letters, numbers, and shapes. The activity center also helps babies develop fine motor skills and gross motor skills.	49.99	34.99	VTech	\N	\N	\N	Activity Centers	\N	\N
911	\N	\N	Fisher-Price Little People Animal Sounds Farm	Fisher-Price Little People Animal Sounds Farm is a great gift for toddlers. It features a variety of farm animals that make realistic sounds. The farm also helps toddlers develop fine motor skills and problem-solving skills.	29.99	19.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
912	\N	\N	Kids Toy Car	Detailed toy car with realistic features, lights and sounds.	20	16	Imagination Toys	\N	\N	\N	Cars	\N	\N
913	\N	\N	Toy Train Set	Complete train set with tracks, train engine, and carriages.	30	24	Imagination Toys	\N	\N	\N	Trains	\N	\N
914	\N	\N	Building Blocks	Set of colorful building blocks for creative play.	15	12	Learning Toys	\N	\N	\N	Building	\N	\N
915	\N	\N	Play Kitchen	Interactive play kitchen with pretend appliances and accessories.	40	32	Imagination Toys	\N	\N	\N	Kitchen	\N	\N
916	\N	\N	Toy Dollhouse	Detailed dollhouse with multiple rooms and furniture.	35	28	Imagination Toys	\N	\N	\N	Dollhouses	\N	\N
917	\N	\N	Stuffed Animal Dog	Soft and cuddly stuffed animal dog.	18	14	Imagination Toys	\N	\N	\N	Animals	\N	\N
918	\N	\N	Stuffed Animal Bear	Soft and huggable stuffed animal bear.	20	16	Imagination Toys	\N	\N	\N	Animals	\N	\N
919	\N	\N	Toy Cash Register	Realistic cash register with pretend money and scanner.	25	20	Imagination Toys	\N	\N	\N	Pretend Play	\N	\N
920	\N	\N	Toy Vacuum Cleaner	Pretend play vacuum cleaner with realistic sounds.	12	10	Imagination Toys	\N	\N	\N	Pretend Play	\N	\N
921	\N	\N	Toy Tool Set	Set of pretend play tools for imaginative play.	18	14	Imagination Toys	\N	\N	\N	Tools	\N	\N
922	\N	\N	Art Supplies	Set of colorful art supplies for drawing, painting, and crafting.	20	16	Learning Toys	\N	\N	\N	Art	\N	\N
923	\N	\N	Musical Instrument Set	Set of musical instruments for pretend play.	25	20	Learning Toys	\N	\N	\N	Music	\N	\N
924	\N	\N	Board Game	Classic board game for family fun.	15	12	Learning Toys	\N	\N	\N	Games	\N	\N
925	\N	\N	Card Game	Educational card game for learning and development.	10	8	Learning Toys	\N	\N	\N	Games	\N	\N
926	\N	\N	Puzzle	Colorful puzzle for problem-solving and cognitive skills.	12	10	Learning Toys	\N	\N	\N	Puzzles	\N	\N
927	\N	\N	Science Experiment Kit	Fun and educational science experiment kit.	20	16	Learning Toys	\N	\N	\N	Science	\N	\N
928	\N	\N	Toy Microscope	Pretend play microscope for exploring the world.	15	12	Learning Toys	\N	\N	\N	Science	\N	\N
929	\N	\N	Toy Telescope	Pretend play telescope for stargazing and exploration.	18	14	Learning Toys	\N	\N	\N	Science	\N	\N
930	\N	\N	Action Figure	Detailed action figure from a popular movie or TV show.	15	12	Imagination Toys	\N	\N	\N	Action Figures	\N	\N
931	\N	\N	Superhero Cape	Pretend play superhero cape for imaginative play.	10	8	Imagination Toys	\N	\N	\N	Superheroes	\N	\N
932	\N	\N	Princess Dress Up	Pretend play princess dress up for imaginative play.	20	16	Imagination Toys	\N	\N	\N	Dress Up	\N	\N
933	\N	\N	Toy Sword	Pretend play sword for imaginative play.	12	10	Imagination Toys	\N	\N	\N	Weapons	\N	\N
934	\N	\N	Toy Bow and Arrow	Pretend play bow and arrow for imaginative play.	15	12	Imagination Toys	\N	\N	\N	Weapons	\N	\N
935	\N	\N	Remote Control Car	High-speed remote control car for racing and stunts.	30	24	Imagination Toys	\N	\N	\N	Cars	\N	\N
936	\N	\N	Stuffed Animal Elephant	Soft and cuddly stuffed animal elephant.	25	20	Imagination Toys	\N	\N	\N	Animals	\N	\N
937	\N	\N	Stuffed Animal Giraffe	Soft and cuddly stuffed animal giraffe.	28	22	Imagination Toys	\N	\N	\N	Animals	\N	\N
938	\N	\N	Toy Farm Set	Complete farm set with animals, barn, and accessories.	35	28	Imagination Toys	\N	\N	\N	Farm	\N	\N
939	\N	\N	Toy Airplane	Detailed toy airplane with realistic features.	20	16	Imagination Toys	\N	\N	\N	Planes	\N	\N
940	\N	\N	Toy Helicopter	Detailed toy helicopter with realistic features.	18	14	Imagination Toys	\N	\N	\N	Planes	\N	\N
941	\N	\N	Toy Rocket Ship	Detailed toy rocket ship with realistic features.	20	16	Imagination Toys	\N	\N	\N	Space	\N	\N
942	\N	\N	Toy Fire Truck	Detailed toy fire truck with realistic features.	30	24	Imagination Toys	\N	\N	\N	Vehicles	\N	\N
943	\N	\N	Toy Police Car	Detailed toy police car with realistic features.	20	16	Imagination Toys	\N	\N	\N	Vehicles	\N	\N
944	\N	\N	Toy Ambulance	Detailed toy ambulance with realistic features.	25	20	Imagination Toys	\N	\N	\N	Vehicles	\N	\N
945	\N	\N	Action Figure, Captain America, 6-inch, with Shield and Accessories	Captain America figure with poseable arms and legs, molded detailing, and signature shield. Perfect for imaginative play and storytelling.	14.99	11.99	Marvel	\N	\N	\N	Action Figures	\N	\N
946	\N	\N	Playmobil Fire Station	Interactive playset featuring a fire station building, vehicles, and firefighters.	39.99	29.99	Playmobil	\N	\N	\N	Playsets	\N	\N
947	\N	\N	Doll, Barbie Dreamhouse, with Furniture and Accessories	Barbie doll with signature style and long blonde hair, Dreamhouse with multiple rooms and accessories, including a kitchen, bathroom, living room, and bedroom.	29.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
948	\N	\N	Building Set, LEGO City Police Station, 400+ Pieces	LEGO City Police Station with multiple levels, jail cells, police vehicles, and accessories. Encourages creativity and problem-solving skills.	49.99	39.99	LEGO	\N	\N	\N	Building Sets	\N	\N
979	\N	\N	Dollhouse	Pink dollhouse with 3 levels and 4 rooms	24.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
949	\N	\N	Board Game, Monopoly Junior, for Ages 5+	Monopoly game designed for younger players, with simplified rules and colorful board. Introduces basic money management and property trading concepts.	14.99	10.99	Hasbro	\N	\N	\N	Board Games	\N	\N
950	\N	\N	Craft Kit, Crayola Ultimate Crayon Collection, 150 Crayons	Crayola crayon collection with 150 vibrant colors, perfect for drawing, coloring, and creating. Encourages artistic expression and imagination.	19.99	14.99	Crayola	\N	\N	\N	Craft Kits	\N	\N
951	\N	\N	Puzzle, Ravensburger Enchanted Forest, 1000 Pieces	Ravensburger puzzle featuring a vibrant and detailed image of an enchanted forest, with intricate details and multiple layers.	14.99	10.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
952	\N	\N	Stuffed Animal, Melissa & Doug Lion Plush, 12-inch	Soft and cuddly lion plush with realistic features, perfect for snuggling and imaginative play.	19.99	14.99	Melissa & Doug	\N	\N	\N	Stuffed Animals	\N	\N
953	\N	\N	Toy Vehicle, Hot Wheels Monster Truck, Assorted	Assortment of Hot Wheels Monster Trucks with oversized tires, unique designs, and real-life detailing. Encourages imaginative play and vehicle exploration.	4.99	3.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
954	\N	\N	Science Kit, National Geographic Mega Science Kit, 150+ Experiments	Mega science kit with over 150 experiments covering physics, chemistry, biology, and more. Includes materials, instructions, and a guide for hands-on learning.	49.99	39.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
955	\N	\N	Playset, Fisher-Price Little People Farm, with Animals and Tractor	Little People Farm playset with barn, tractor, and various farm animals. Encourages imaginative play, storytelling, and social skills.	29.99	24.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
956	\N	\N	Doll, Disney Princess Snow White, Singing and Interactive	Snow White doll with iconic blue and yellow dress, that sings songs and interacts with accessories. Encourages imaginative play and storytelling based on the classic fairy tale.	24.99	19.99	Disney	\N	\N	\N	Dolls	\N	\N
957	\N	\N	Building Set, Mega Bloks First Builders Big Building Bag, 80 Blocks	Mega Bloks building blocks in various shapes and colors, perfect for toddlers to develop fine motor skills and creativity.	14.99	9.99	Mega Bloks	\N	\N	\N	Building Sets	\N	\N
958	\N	\N	Toy Vehicle, Matchbox Moving Parts Dump Truck	Dump truck with movable parts, realistic detailing, and sound effects. Encourages imaginative play and vehicle exploration.	4.99	3.99	Matchbox	\N	\N	\N	Toy Vehicles	\N	\N
959	\N	\N	Board Game, Candy Land, for Ages 3+	Candy Land game for young children, with a sweet and colorful board and simple rules. Introduces basic counting and color recognition skills.	10.99	7.99	Hasbro	\N	\N	\N	Board Games	\N	\N
960	\N	\N	Craft Kit, LEGO DOTS Funky Bracelets, Customizable	LEGO DOTS bracelet-making kit with colorful tiles, charms, and adjustable bands. Encourages creativity, self-expression, and fine motor skills.	14.99	10.99	LEGO	\N	\N	\N	Craft Kits	\N	\N
961	\N	\N	Stuffed Animal, Ty Beanie Boo's Rainbow the Unicorn	Rainbow the Unicorn beanie boo with sparkly eyes, soft fur, and a unique design. Perfect for cuddling and imaginative play.	12.99	9.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
962	\N	\N	Toy Vehicle, Hot Wheels 5-Car Pack, Assorted	Assortment of 5 Hot Wheels cars with unique designs and real-life detailing. Encourages imaginative play and vehicle exploration.	14.99	10.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
963	\N	\N	Science Kit, Thames & Kosmos Kids First Chemistry Lab	Kids First Chemistry Lab kit with 30+ experiments, materials, and instructions. Introduces basic chemistry concepts and hands-on learning.	29.99	24.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
964	\N	\N	Playset, Playmobil Princess Castle, with Accessories	Playmobil Princess Castle playset with multiple rooms, furniture, and accessories. Encourages imaginative play, storytelling, and social skills.	49.99	39.99	Playmobil	\N	\N	\N	Playsets	\N	\N
965	\N	\N	Doll, American Girl Bitty Baby, Blonde Hair and Blue Eyes	Bitty Baby doll with blonde hair, blue eyes, and a soft body. Perfect for nurturing and imaginative play.	29.99	24.99	American Girl	\N	\N	\N	Dolls	\N	\N
966	\N	\N	Building Set, K'NEX Thrill Rides Roller Coaster, 450+ Pieces	K'NEX Thrill Rides Roller Coaster building set with over 450 pieces, motorized parts, and track. Encourages creativity, problem-solving skills, and STEM learning.	49.99	39.99	K'NEX	\N	\N	\N	Building Sets	\N	\N
967	\N	\N	Toy Vehicle, PAW Patrol Chase's Police Cruiser	Chase's Police Cruiser toy vehicle with lights, sounds, and a working claw. Perfect for imaginative play based on the popular TV show.	19.99	14.99	PAW Patrol	\N	\N	\N	Toy Vehicles	\N	\N
968	\N	\N	Board Game, Operation, for Ages 6+	Operation game with tweezers and a patient's body with various ailments. Encourages hand-eye coordination and fine motor skills.	14.99	10.99	Hasbro	\N	\N	\N	Board Games	\N	\N
969	\N	\N	Craft Kit, Crayola Air-Dry Clay, 24-Pack	Crayola Air-Dry Clay in multiple colors, perfect for modeling, sculpting, and creating. Encourages creativity, fine motor skills, and sensory play.	19.99	14.99	Crayola	\N	\N	\N	Craft Kits	\N	\N
970	\N	\N	Stuffed Animal, Jellycat Bashful Bunny, Medium	Bashful Bunny stuffed animal with soft fur, floppy ears, and a sweet expression. Perfect for cuddling and imaginative play.	19.99	14.99	Jellycat	\N	\N	\N	Stuffed Animals	\N	\N
971	\N	\N	Toy Vehicle, Hot Wheels Semi Truck with Trailer	Hot Wheels Semi Truck with detachable trailer, realistic detailing, and multiple play features. Encourages imaginative play and vehicle exploration.	19.99	14.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
972	\N	\N	Science Kit, National Geographic Kids Gross Science Lab	Gross Science Lab kit with over 20 experiments and materials. Introduces basic biology and chemistry concepts while exploring icky and fascinating science.	29.99	24.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
973	\N	\N	Playset, LEGO City Fire Station, with Fire Truck and Accessories	LEGO City Fire Station playset with multiple levels, fire engine, ladder truck, and accessories. Encourages imaginative play, storytelling, and STEM learning.	49.99	39.99	LEGO	\N	\N	\N	Playsets	\N	\N
974	\N	\N	Doll, LOL Surprise! OMG House of Surprises	LOL Surprise! OMG House of Surprises with multiple rooms, furniture, and accessories. Perfect for imaginative play, storytelling, and collecting surprises.	49.99	39.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
975	\N	\N	Building Set, Mega Construx Halo Infinite Warthog Run	Halo Infinite Warthog Run building set with over 500 pieces, motorized Warthog vehicle, and Spartan figures. Encourages creativity, problem-solving skills, and STEM learning.	49.99	39.99	Mega Construx	\N	\N	\N	Building Sets	\N	\N
976	\N	\N	Toy Vehicle, Fisher-Price Little People Sit 'n Stand Skyway	Little People Sit 'n Stand Skyway playset with multiple levels, vehicles, and accessories. Encourages imaginative play, storytelling, and fine motor skills.	29.99	24.99	Fisher-Price	\N	\N	\N	Toy Vehicles	\N	\N
977	\N	\N	Board Game, Trouble, for Ages 5+	Trouble game with spinning die, game board, and colorful pegs. Introduces basic strategy and social skills.	10.99	7.99	Hasbro	\N	\N	\N	Board Games	\N	\N
981	\N	\N	Action Figure	Superman action figure with movable joints	12.99	9.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
982	\N	\N	Board Game	Monopoly board game for 2-4 players	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
983	\N	\N	Play Kitchen	Wooden play kitchen with oven, stove, and sink	49.99	39.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
984	\N	\N	Craft Kit	Unicorn craft kit with glitter, stickers, and paint	14.99	11.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
985	\N	\N	Stuffed Animal	Soft and cuddly teddy bear	19.99	14.99	Teddy Bear Factory	\N	\N	\N	Stuffed Animals	\N	\N
986	\N	\N	Science Kit	Chemistry science kit with experiments and chemicals	24.99	19.99	National Geographic	\N	\N	\N	Science	\N	\N
987	\N	\N	Musical Instrument	Toy piano with 8 keys and 2 octaves	19.99	14.99	Fisher-Price	\N	\N	\N	Musical Instruments	\N	\N
988	\N	\N	Video Game	Super Mario Odyssey video game for Nintendo Switch	59.99	49.99	Nintendo	\N	\N	\N	Video Games	\N	\N
989	\N	\N	Book	Harry Potter and the Sorcerer's Stone book	12.99	9.99	J.K. Rowling	\N	\N	\N	Books	\N	\N
990	\N	\N	Puzzle	100-piece puzzle with a farm scene	14.99	11.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
991	\N	\N	Ride-On Toy	Blue ride-on car with working horn and lights	49.99	39.99	Little Tikes	\N	\N	\N	Ride-On Toys	\N	\N
992	\N	\N	Outdoor Toy	Swing set with 2 swings and a slide	199.99	149.99	Lifetime	\N	\N	\N	Outdoor Toys	\N	\N
993	\N	\N	Party Supplies	Pack of 100 balloons in assorted colors	9.99	7.99	Party City	\N	\N	\N	Party Supplies	\N	\N
994	\N	\N	Candy	Bag of gummy bears	2.99	1.99	Haribo	\N	\N	\N	Candy	\N	\N
995	\N	\N	Chocolate	Chocolate bar with milk chocolate	3.99	2.99	Hershey's	\N	\N	\N	Chocolate	\N	\N
996	\N	\N	Cookies	Box of chocolate chip cookies	4.99	3.99	Chips Ahoy	\N	\N	\N	Cookies	\N	\N
997	\N	\N	Soda	Can of Coca-Cola	1.99	1.49	Coca-Cola	\N	\N	\N	Soda	\N	\N
998	\N	\N	Water	Bottle of water	1.49	0.99	Aquafina	\N	\N	\N	Water	\N	\N
999	\N	\N	Popcorn	Bag of microwave popcorn	3.99	2.99	Jiffy Pop	\N	\N	\N	Popcorn	\N	\N
1000	\N	\N	Chips	Bag of potato chips	3.99	2.99	Lay's	\N	\N	\N	Chips	\N	\N
1001	\N	\N	Pretzels	Box of pretzels	2.99	1.99	Rold Gold	\N	\N	\N	Pretzels	\N	\N
1002	\N	\N	Fruit	Apple	1.49	0.99	N/A	\N	\N	\N	Fruit	\N	\N
1003	\N	\N	Vegetable	Carrot	1.99	1.49	N/A	\N	\N	\N	Vegetables	\N	\N
1004	\N	\N	Dairy	Milk	3.99	2.99	N/A	\N	\N	\N	Dairy	\N	\N
1005	\N	\N	Meat	Chicken breast	6.99	4.99	N/A	\N	\N	\N	Meat	\N	\N
1006	\N	\N	Fish	Salmon	9.99	7.99	N/A	\N	\N	\N	Fish	\N	\N
1007	\N	\N	Eggs	Dozen eggs	2.99	1.99	N/A	\N	\N	\N	Eggs	\N	\N
1008	\N	\N	Bread	Loaf of bread	2.99	1.99	N/A	\N	\N	\N	Bread	\N	\N
1009	\N	\N	Rice	Bag of rice	4.99	3.99	N/A	\N	\N	\N	Rice	\N	\N
1010	\N	\N	Pasta	Box of pasta	2.99	1.99	N/A	\N	\N	\N	Pasta	\N	\N
1011	\N	\N	Cereal	Box of cereal	3.99	2.99	N/A	\N	\N	\N	Cereal	\N	\N
1012	\N	\N	Star Wars Lightsaber	Extendable lightsaber toy with light and sound effects, featuring iconic Star Wars designs.	29.99	19.99	Star Wars	\N	\N	\N	Action Figures	\N	\N
1013	\N	\N	Barbie Dreamhouse	Multi-level dollhouse with multiple rooms, furniture, and accessories.	49.99	39.99	Barbie	\N	\N	\N	Dolls	\N	\N
1014	\N	\N	Hot Wheels Track Set	Large-scale track set with multiple jumps, loops, and motorized cars.	39.99	29.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1015	\N	\N	My Little Pony Friendship Castle	Interactive playset with castle, ponies, and accessories.	34.99	24.99	My Little Pony	\N	\N	\N	Playsets	\N	\N
1016	\N	\N	LEGO City Police Station	Detailed police station building set with vehicles, minifigures, and accessories.	49.99	39.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1017	\N	\N	Nerf Fortnite Pump SG	Pump-action shotgun toy inspired by the popular Fortnite video game.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
1018	\N	\N	Paw Patrol Lookout Tower	Interactive playset featuring the Paw Patrol headquarters with multiple levels and vehicles.	44.99	34.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
1019	\N	\N	Minecraft Creeper Plush	Soft and cuddly plush toy shaped like the iconic Minecraft Creeper character.	14.99	9.99	Minecraft	\N	\N	\N	Plush Toys	\N	\N
1020	\N	\N	LOL Surprise! Doll	Collectible doll with multiple layers of surprises and accessories.	10.99	7.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1021	\N	\N	Play-Doh Modeling Compound	Set of colorful, non-toxic modeling compound for creative play.	9.99	6.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1022	\N	\N	Melissa & Doug Wooden Kitchen	Interactive wooden play kitchen with realistic appliances and accessories.	49.99	39.99	Melissa & Doug	\N	\N	\N	Play Kitchens	\N	\N
1023	\N	\N	American Girl Doll	18-inch doll with realistic features, clothing, and accessories.	119.99	99.99	American Girl	\N	\N	\N	Dolls	\N	\N
1024	\N	\N	BeyBlade Burst Turbo Slingshock Starter Pack	Top-spinning toy with launcher and accessories.	19.99	14.99	BeyBlade Burst	\N	\N	\N	Spinning Tops	\N	\N
1025	\N	\N	Hatchimals Pixies Crystal Flyers	Collectible flying toy shaped like fairies with light-up wings.	14.99	9.99	Hatchimals	\N	\N	\N	Collectibles	\N	\N
1026	\N	\N	Funko Pop! Marvel Spider-Man	Collectible vinyl figure of Spider-Man.	10.99	7.99	Funko Pop!	\N	\N	\N	Collectibles	\N	\N
1027	\N	\N	Roblox Adopt Me! Pet Plush	Soft and cuddly plush toy shaped like a popular pet from the Roblox game.	19.99	14.99	Roblox	\N	\N	\N	Plush Toys	\N	\N
1028	\N	\N	Squishmallows 12-Inch Plush	Soft and squishy plush toy in various adorable animal designs.	14.99	9.99	Squishmallows	\N	\N	\N	Plush Toys	\N	\N
1029	\N	\N	Crayola Washable Crayons	Set of 24 washable crayons for colorful drawing and creativity.	5.99	3.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1030	\N	\N	Kinetic Sand	Magical play sand that moves and molds without drying out.	9.99	6.99	Kinetic Sand	\N	\N	\N	Sensory Play	\N	\N
1031	\N	\N	Stroller	Lightweight stroller with a foldable design	100.00	80.00	Baby Jogger	\N	\N	\N	Strollers	\N	\N
1032	\N	\N	Mega Bloks First Builders	Large building blocks designed for young children to encourage creativity and fine motor skills.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Sets	\N	\N
1033	\N	\N	Little Tikes Cozy Coupe	Classic ride-on toy with a steering wheel, horn, and storage compartment.	49.99	39.99	Little Tikes	\N	\N	\N	Ride-On Toys	\N	\N
1034	\N	\N	Fisher-Price Imaginext Batcave	Interactive playset featuring the Batcave from the Batman universe.	44.99	34.99	Fisher-Price	\N	\N	\N	Playsets	\N	\N
1035	\N	\N	VTech Kidizoom Smartwatch DX2	Interactive smartwatch with games, camera, and messaging features.	59.99	49.99	VTech	\N	\N	\N	Electronics	\N	\N
1036	\N	\N	Disney Princess Elsa Singing Doll	Musical doll of Elsa from the Frozen movie that sings and interacts with children.	34.99	24.99	Disney Princess	\N	\N	\N	Dolls	\N	\N
1037	\N	\N	Ravensburger GraviTrax Starter Set	Marble run construction system with tracks, tiles, and accessories for creative building and experimentation.	49.99	39.99	Ravensburger	\N	\N	\N	Building Sets	\N	\N
1038	\N	\N	Melissa & Doug Magnetic Dress-Up Doll	Wooden doll with magnetic clothing and accessories for imaginative play.	24.99	19.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
1039	\N	\N	Nerf Rival Kronos XVIII-500	High-powered blaster with spring-action firing and capacity for 50 rounds.	34.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
1040	\N	\N	LEGO Ninjago Spinjitzu Burst Lloyd	Buildable and interactive toy featuring Lloyd, the Green Ninja, with spinning top and accessories.	19.99	14.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1041	\N	\N	Crayola Washable Markers	Set of 10 washable markers for colorful drawing, writing, and creativity.	7.99	5.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1042	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Interactive playset featuring an ice cream truck with multiple molds, accessories, and play dough.	39.99	29.99	Play-Doh	\N	\N	\N	Play Kitchens	\N	\N
1043	\N	\N	Barbie Dreamtopia Mermaid Doll	Mermaid doll with colorful tail, tiara, and accessories.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1044	\N	\N	Hot Wheels 5-Car Gift Pack	Set of five Hot Wheels cars in various designs and colors.	14.99	9.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1045	\N	\N	Melissa & Doug Wooden Peg Puzzle	Set of wooden pegs and puzzle board with colorful animal designs.	12.99	9.99	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
1046	\N	\N	LEGO Classic Creative Brick Box	Large box of colorful LEGO bricks in various shapes and sizes for endless creative building.	49.99	39.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1047	\N	\N	Toy Car	Red and blue toy car with realistic engine sounds and working headlights	10.99	8.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1048	\N	\N	Building Blocks	Set of 100 colorful building blocks in various shapes and sizes	14.99	11.99	Mega Bloks	\N	\N	\N	Building	\N	\N
1049	\N	\N	Action Figure	Superhero action figure with movable joints and interchangeable accessories	12.99	9.99	Marvel	\N	\N	\N	Action Figures	\N	\N
1050	\N	\N	Doll	Pretty doll with long blonde hair and a beautiful dress	14.99	11.99	Barbie	\N	\N	\N	Dolls	\N	\N
1051	\N	\N	Board Game	Classic board game for 2-4 players, involving strategy and luck	19.99	15.99	Monopoly	\N	\N	\N	Board Games	\N	\N
1052	\N	\N	Puzzle	100-piece puzzle with a colorful image of a farm	9.99	7.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1053	\N	\N	Stuffed Animal	Soft and cuddly stuffed animal shaped like a teddy bear	19.99	14.99	Build-A-Bear	\N	\N	\N	Stuffed Animals	\N	\N
1054	\N	\N	Play Kitchen	Interactive play kitchen with realistic appliances and accessories	49.99	39.99	KidKraft	\N	\N	\N	Pretend Play	\N	\N
1055	\N	\N	Science Kit	Hands-on science kit with experiments and activities in various scientific fields	29.99	24.99	National Geographic	\N	\N	\N	Science	\N	\N
1056	\N	\N	Art Set	Complete art set with crayons, markers, paint, and brushes	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1057	\N	\N	Lego Set	Building set with colorful Lego bricks and instructions to create a variety of models	29.99	24.99	Lego	\N	\N	\N	Building	\N	\N
1058	\N	\N	Nerf Gun	Foam-dart shooting toy gun with multiple firing modes	19.99	14.99	Nerf	\N	\N	\N	Outdoor Toys	\N	\N
1059	\N	\N	Scooter	Foldable scooter with adjustable handlebars and a sturdy frame	49.99	39.99	Razor	\N	\N	\N	Outdoor Toys	\N	\N
1060	\N	\N	Trampoline	Small trampoline with a safety net for outdoor play	99.99	79.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
1061	\N	\N	Playhouse	Colorful and spacious playhouse with a slide and climbing wall	149.99	119.99	Step2	\N	\N	\N	Outdoor Toys	\N	\N
1062	\N	\N	Video Game	Action-adventure video game with immersive gameplay and stunning graphics	59.99	49.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1063	\N	\N	Book	Chapter book with an exciting story about a young adventurer	7.99	5.99	Scholastic	\N	\N	\N	Books	\N	\N
1064	\N	\N	Craft Kit	Craft kit with materials and instructions to make a variety of fun projects	14.99	11.99	Klutz	\N	\N	\N	Crafts	\N	\N
1065	\N	\N	Musical Instrument	Toy piano with 25 keys and realistic sounds	29.99	24.99	Casio	\N	\N	\N	Musical Instruments	\N	\N
1066	\N	\N	Remote Control Car	Fast and agile remote control car with rechargeable battery	79.99	69.99	Traxxas	\N	\N	\N	Outdoor Toys	\N	\N
1067	\N	\N	Dollhouse	Detailed and spacious dollhouse with furniture and accessories	49.99	39.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
1068	\N	\N	Train Set	Electric train set with tracks, engine, and multiple cars	99.99	79.99	Lionel	\N	\N	\N	Trains	\N	\N
1069	\N	\N	Chemistry Set	Comprehensive chemistry set with chemicals and equipment for various experiments	49.99	39.99	Thames & Kosmos	\N	\N	\N	Science	\N	\N
1070	\N	\N	Microscope	Basic microscope for observing small objects up close	29.99	24.99	National Geographic	\N	\N	\N	Science	\N	\N
1071	\N	\N	Dress-Up Clothes	Set of dress-up clothes with different costumes and accessories	29.99	24.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
1072	\N	\N	Play Tent	Spacious and colorful play tent with a fun design	24.99	19.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
1073	\N	\N	Sandpit	Large sandpit with a cover to protect from the elements	79.99	69.99	Little Tikes	\N	\N	\N	Outdoor Toys	\N	\N
1074	\N	\N	Water Table	Interactive water table with pumps, fountains, and water toys	49.99	39.99	Step2	\N	\N	\N	Outdoor Toys	\N	\N
1075	\N	\N	Kite	Large and colorful kite with a long tail	14.99	11.99	Intex	\N	\N	\N	Outdoor Toys	\N	\N
1076	\N	\N	Bubbles	Large bottle of bubbles with a bubble wand	4.99	3.99	Gazillion	\N	\N	\N	Outdoor Toys	\N	\N
1077	\N	\N	Chalk	Set of colorful chalk in various shapes and sizes	7.99	5.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1078	\N	\N	Play-Doh	Set of colorful and soft Play-Doh for creative play	9.99	7.99	Hasbro	\N	\N	\N	Arts & Crafts	\N	\N
1079	\N	\N	Slime Kit	Kit with ingredients and instructions to make your own slime	14.99	11.99	Elmer's	\N	\N	\N	Arts & Crafts	\N	\N
1080	\N	\N	Magnetic Tiles	Set of magnetic tiles in different shapes and colors for building and creativity	29.99	24.99	Magna-Tiles	\N	\N	\N	Building	\N	\N
1081	\N	\N	Robot Kit	Build-it-yourself robot kit with motors, sensors, and a remote control	49.99	39.99	Lego	\N	\N	\N	Science	\N	\N
1082	\N	\N	Action Figure, Superhero	Highly detailed action figure of popular superhero, with multiple points of articulation and accessories	19.99	14.99	XYZ Toys	\N	\N	\N	Action Figures	\N	\N
1083	\N	\N	Doll, Princess	Beautiful princess doll with long flowing hair, sparkly dress, and tiara	24.99	19.99	ABC Dolls	\N	\N	\N	Dolls	\N	\N
1084	\N	\N	Board Game, Adventure	Cooperative board game for 2-4 players, with exciting challenges and quests	29.99	24.99	XYZ Games	\N	\N	\N	Board Games	\N	\N
1085	\N	\N	Building Blocks, Classic	Classic building blocks in various colors and shapes, for endless imaginative play	19.99	14.99	DEF Blocks	\N	\N	\N	Building Blocks	\N	\N
1086	\N	\N	Toy Car, Race Car	Fast and furious race car toy with realistic details, sound effects, and lights	24.99	19.99	GHI Toys	\N	\N	\N	Toy Cars	\N	\N
1087	\N	\N	Slime Kit, Unicorn	Magical slime kit with everything needed to create sparkly, colorful, unicorn-themed slime	14.99	10.99	XYZ Crafts	\N	\N	\N	Slime Kits	\N	\N
1088	\N	\N	Science Kit, Volcano	Educational science kit to create a bubbling, erupting volcano	19.99	14.99	ABC Science	\N	\N	\N	Science Kits	\N	\N
1089	\N	\N	Play Kitchen, Modern	Stylish and realistic play kitchen with stove, oven, sink, and accessories	49.99	39.99	GHI Playsets	\N	\N	\N	Play Kitchens	\N	\N
1090	\N	\N	Art Set, Drawing and Painting	Complete art set with pencils, crayons, markers, paints, and paper	24.99	19.99	XYZ Arts	\N	\N	\N	Art Sets	\N	\N
1091	\N	\N	Stuffed Animal, Bear	Cute and cuddly teddy bear with soft fur and embroidered eyes	14.99	10.99	ABC Plush	\N	\N	\N	Stuffed Animals	\N	\N
1092	\N	\N	Nerf Gun, Foam Dart Blaster	High-powered Nerf gun with foam darts for thrilling action	29.99	24.99	GHI Blasters	\N	\N	\N	Nerf Guns	\N	\N
1093	\N	\N	Puzzle, Animal Safari	Colorful puzzle with animal designs, perfect for developing problem-solving skills	14.99	10.99	XYZ Puzzles	\N	\N	\N	Puzzles	\N	\N
1094	\N	\N	Toy Train Set, Classic	Traditional toy train set with tracks, locomotive, and cars	49.99	39.99	ABC Trains	\N	\N	\N	Toy Trains	\N	\N
1095	\N	\N	Dress-Up Set, Princess	Sparkling and elegant dress-up set with princess gown, accessories, and shoes	29.99	24.99	GHI Dress-Up	\N	\N	\N	Dress-Up Sets	\N	\N
1096	\N	\N	Action Figure, Dinosaur	Realistic and detailed dinosaur action figure, perfect for imaginative play	24.99	19.99	XYZ Toys	\N	\N	\N	Action Figures	\N	\N
1097	\N	\N	Doll, Fairy	Enchanted fairy doll with glittery wings and magical accessories	19.99	14.99	ABC Dolls	\N	\N	\N	Dolls	\N	\N
1098	\N	\N	Board Game, Strategy	Challenging strategy board game for 2-4 players, with multiple game modes	29.99	24.99	XYZ Games	\N	\N	\N	Board Games	\N	\N
1099	\N	\N	Building Blocks, Magnetic	Magnetic building blocks in various shapes and colors, for creative construction	24.99	19.99	DEF Blocks	\N	\N	\N	Building Blocks	\N	\N
1100	\N	\N	Toy Car, Monster Truck	Monster truck toy with oversized tires and rugged design, for crashing and smashing	29.99	24.99	GHI Toys	\N	\N	\N	Toy Cars	\N	\N
1101	\N	\N	Slime Kit, Glow-in-the-Dark	Amazing glow-in-the-dark slime kit, for creating spooky and luminous slime	19.99	14.99	XYZ Crafts	\N	\N	\N	Slime Kits	\N	\N
1102	\N	\N	Science Kit, Solar System	Fascinating science kit to explore the wonders of the solar system	24.99	19.99	ABC Science	\N	\N	\N	Science Kits	\N	\N
1103	\N	\N	Play Kitchen, Gourmet	Realistic and interactive play kitchen with stove, oven, refrigerator, and pretend food	69.99	59.99	GHI Playsets	\N	\N	\N	Play Kitchens	\N	\N
1104	\N	\N	Art Set, Creative Studio	Deluxe art set with a wide variety of materials, including paints, markers, pencils, and clay	49.99	39.99	XYZ Arts	\N	\N	\N	Art Sets	\N	\N
1105	\N	\N	Stuffed Animal, Unicorn	Mythical and magical unicorn stuffed animal with soft fur and sparkly mane	19.99	14.99	ABC Plush	\N	\N	\N	Stuffed Animals	\N	\N
1106	\N	\N	Nerf Gun, Elite Blaster	Advanced Nerf blaster with improved accuracy and power	39.99	34.99	GHI Blasters	\N	\N	\N	Nerf Guns	\N	\N
1107	\N	\N	Puzzle, World Map	Educational puzzle with a detailed map of the world, perfect for learning about geography	19.99	14.99	XYZ Puzzles	\N	\N	\N	Puzzles	\N	\N
1108	\N	\N	Toy Train Set, Adventure	Exciting toy train set with loop-de-loop track, bridge, and train station	69.99	59.99	ABC Trains	\N	\N	\N	Toy Trains	\N	\N
1109	\N	\N	Dress-Up Set, Superhero	Powerful and heroic dress-up set with superhero costume, mask, and accessories	29.99	24.99	GHI Dress-Up	\N	\N	\N	Dress-Up Sets	\N	\N
1110	\N	\N	Action Figure, Ninja	Agile and skilled ninja action figure with multiple weapons and accessories	29.99	24.99	XYZ Toys	\N	\N	\N	Action Figures	\N	\N
1111	\N	\N	Doll, Mermaid	Beautiful and enchanting mermaid doll with glittery tail and accessories	24.99	19.99	ABC Dolls	\N	\N	\N	Dolls	\N	\N
1112	\N	\N	Board Game, Cooperative	Fun and challenging cooperative board game for 2-4 players, where teamwork is essential	29.99	24.99	XYZ Games	\N	\N	\N	Board Games	\N	\N
1113	\N	\N	Building Blocks, Educational	Colorful and interactive building blocks with letters, numbers, and shapes	24.99	19.99	DEF Blocks	\N	\N	\N	Building Blocks	\N	\N
1114	\N	\N	Toy Car, Remote Control	High-speed remote control car with sleek design and multiple functions	39.99	34.99	GHI Toys	\N	\N	\N	Toy Cars	\N	\N
1115	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	The Nerf Fortnite SP-L Elite Dart Blaster is inspired by the blaster used in Fortnite, capturing the look and colors of the popular video game. It fires Elite darts up to 90 feet (27 meters) and comes with 6 Elite darts. The blaster has a rotating drum that holds 3 darts and a pump-action priming mechanism.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
1116	\N	\N	Barbie Dreamhouse Adventures Camper Playset	The Barbie Dreamhouse Adventures Camper Playset is a 3-in-1 vehicle that transforms into a camper, pool, and play area. It comes with a Barbie doll, her puppy, and accessories like a campfire, picnic table, and sleeping bags.	29.99	24.99	Barbie	\N	\N	\N	Dolls	\N	\N
1117	\N	\N	Hot Wheels Monster Trucks Megalodon Storm RC Vehicle	The Hot Wheels Monster Trucks Megalodon Storm RC Vehicle is a remote-controlled monster truck that looks like a giant shark. It has a pivoting bite attack, chomping sounds, and light-up eyes.	49.99	39.99	Hot Wheels	\N	\N	\N	Remote Control Vehicles	\N	\N
1118	\N	\N	LOL Surprise OMG House of Surprises	The LOL Surprise OMG House of Surprises is a 3-story dollhouse with 8 rooms, 90+ surprises, and exclusive OMG dolls. It has a working elevator, a pool, a kitchen, and other realistic details.	109.99	89.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1119	\N	\N	LEGO Star Wars The Mandalorian The Child (Baby Yoda) Building Kit	The LEGO Star Wars The Mandalorian The Child (Baby Yoda) Building Kit is a 1,073-piece set that lets you build a detailed and posable figure of Baby Yoda. It comes with a hoverpram and a display stand.	79.99	69.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1120	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	The Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset is a pretend ice cream truck that lets kids create and decorate their own ice cream treats. It comes with 25 Play-Doh colors, molds, and accessories.	29.99	24.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
1121	\N	\N	VTech KidiZoom Creator Cam	The VTech KidiZoom Creator Cam is a kid-friendly digital camera that lets kids take photos and videos, add special effects, and edit their creations. It has a 5.0-megapixel camera, a 2.4-inch color screen, and built-in games.	59.99	49.99	VTech	\N	\N	\N	Cameras	\N	\N
1122	\N	\N	Nintendo Switch Lite	The Nintendo Switch Lite is a portable game console that lets you play Nintendo Switch games on the go. It has a 5.5-inch LCD screen, a built-in battery, and a slimmer design than the original Nintendo Switch.	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1123	\N	\N	Minecraft Dungeons Ultimate Edition	Minecraft Dungeons Ultimate Edition includes the base game, the Season Pass, and six DLC packs. The game is a dungeon-crawling action-adventure spin-off of the popular Minecraft franchise.	29.99	24.99	Minecraft	\N	\N	\N	Video Games	\N	\N
1124	\N	\N	Fortnite Monopoly Board Game	The Fortnite Monopoly Board Game is a special edition of the classic Monopoly board game themed after the popular video game. It features Fortnite-themed properties, characters, and gameplay.	24.99	19.99	Monopoly	\N	\N	\N	Board Games	\N	\N
1125	\N	\N	Nerf Rival Perses MXVIII-20K Blaster	The Nerf Rival Perses MXVIII-20K Blaster is a fully automatic blaster that fires Rival rounds at a rate of up to 8 rounds per second. It has a 200-round capacity hopper and a rechargeable battery.	99.99	79.99	Nerf	\N	\N	\N	Blasters	\N	\N
1126	\N	\N	LEGO Harry Potter Hogwarts Castle Building Kit	The LEGO Harry Potter Hogwarts Castle Building Kit is a 6,020-piece set that lets you build a detailed and iconic model of Hogwarts Castle. It has movable staircases, secret passages, and 4 minifigures.	399.99	349.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1127	\N	\N	Barbie Rainbow Sparkle Fantasy Hair Mermaid Doll	The Barbie Rainbow Sparkle Fantasy Hair Mermaid Doll is a Barbie doll with rainbow-colored hair that can be styled in different ways. She comes with a brush, hair accessories, and a mermaid tail.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1128	\N	\N	Hot Wheels Criss Cross Crash Track Set	The Hot Wheels Criss Cross Crash Track Set is a track set that lets you race cars through a series of loops, jumps, and obstacles. It comes with two Hot Wheels cars and a launcher.	39.99	29.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
1129	\N	\N	LOL Surprise OMG Remix Super Surprise	The LOL Surprise OMG Remix Super Surprise is a large playset that includes 50+ surprises, including an exclusive OMG doll, fashions, accessories, and a music player.	109.99	89.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1130	\N	\N	LEGO Minecraft The Nether Fortress Building Kit	The LEGO Minecraft The Nether Fortress Building Kit is a 372-piece set that lets you build a detailed and iconic model of a Nether Fortress from the Minecraft video game.	29.99	24.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1131	\N	\N	Paw Patrol Lookout Tower Playset	The Paw Patrol Lookout Tower Playset is a playset that includes a lookout tower, a vehicle, a figure, and accessories. It has lights and sounds, and it can be used to recreate scenes from the Paw Patrol TV show.	59.99	49.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
1132	\N	\N	Hot Wheels Ultimate Garage Playset	The Hot Wheels Ultimate Garage Playset is a large playset with 5 levels, 80+ parking spaces, a helicopter pad, and a car wash. It comes with 2 Hot Wheels cars.	129.99	99.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
1133	\N	\N	Barbie Dream Closet Playset	The Barbie Dream Closet Playset is a playset that includes a wardrobe, a doll, and accessories. The wardrobe has over 25 compartments and can hold over 100 pieces of clothing.	49.99	39.99	Barbie	\N	\N	\N	Playsets	\N	\N
1134	\N	\N	Nerf Fortnite BASR-L Blaster	The Nerf Fortnite BASR-L Blaster is a Fortnite-themed blaster that fires MEGA darts. It has a bolt-action priming mechanism and a 6-dart clip.	39.99	29.99	Nerf	\N	\N	\N	Blasters	\N	\N
1135	\N	\N	LEGO Star Wars AT-AT Building Kit	The LEGO Star Wars AT-AT Building Kit is a 6,785-piece set that lets you build a detailed and iconic model of an AT-AT walker from the Star Wars movies.	799.99	699.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1136	\N	\N	Play-Doh Ultimate Rainbow Creation Station	The Play-Doh Ultimate Rainbow Creation Station is a playset that includes a rainbow-shaped extruder, 28 cans of Play-Doh, and 10 molds. It lets kids create their own rainbow-themed Play-Doh creations.	29.99	24.99	Play-Doh	\N	\N	\N	Playsets	\N	\N
1137	\N	\N	VTech Switch & Go Dinos Velociraptor	The VTech Switch & Go Dinos Velociraptor is a transforming toy that can change from a dinosaur to a race car and back again. It has lights and sounds, and it comes with a driver figure.	29.99	24.99	VTech	\N	\N	\N	Transforming Toys	\N	\N
1138	\N	\N	Nintendo Switch Pro Controller	The Nintendo Switch Pro Controller is a wireless controller designed for the Nintendo Switch. It has a comfortable ergonomic design, motion controls, and HD rumble.	69.99	59.99	Nintendo	\N	\N	\N	Controllers	\N	\N
1139	\N	\N	Minecraft Earth Boost Mini Figure	The Minecraft Earth Boost Mini Figure is a collectible figure that can be used with the Minecraft Earth augmented reality game. It comes with a unique code that can be used to unlock special content in the game.	4.99	3.99	Minecraft	\N	\N	\N	Collectibles	\N	\N
1140	\N	\N	Fortnite Victory Royale Series Cuddle Team Leader Figure	The Fortnite Victory Royale Series Cuddle Team Leader Figure is a 6-inch action figure of the popular Fortnite character. It comes with multiple points of articulation and interchangeable accessories.	19.99	14.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
1141	\N	\N	LEGO Creator 3in1 Pirate Ship Adventure Building Kit	The LEGO Creator 3in1 Pirate Ship Adventure Building Kit is a 3-in-1 building set that lets you build a pirate ship, a skull island, or a tavern. It comes with over 1,200 pieces.	49.99	39.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1142	\N	\N	Play-Doh Super Color Pack	The Play-Doh Super Color Pack includes 20 cans of Play-Doh in a variety of colors. It's perfect for kids who love to create and imagine.	14.99	11.99	Play-Doh	\N	\N	\N	Modeling Clay	\N	\N
1143	\N	\N	VTech Count & Win Sports Center	The VTech Count & Win Sports Center is an interactive playset that helps kids learn about numbers, colors, and shapes. It has lights, sounds, and a variety of sports-themed activities.	29.99	24.99	VTech	\N	\N	\N	Playsets	\N	\N
1144	\N	\N	Nerf Ultra Two Motorized Blaster	The Nerf Ultra Two Motorized Blaster fires darts up to 120 feet (36 meters). It has a motorized flywheel system and a 25-dart capacity drum.	49.99	39.99	Nerf	\N	\N	\N	Blasters	\N	\N
1145	\N	\N	LEGO Minecraft The Creeper Mine Building Kit	The LEGO Minecraft The Creeper Mine Building Kit is a 830-piece set that lets you build a detailed and iconic model of a Creeper mine from the Minecraft video game.	79.99	69.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1146	\N	\N	Toy Train Set, Electric Train with Tracks	Classic electric train set with multiple tracks and train cars.	79.99	59.99	Train Masters	\N	\N	\N	Toy Trains	\N	\N
1147	\N	\N	Barbie Dreamtopia Rainbow Magic Mermaid Doll	The Barbie Dreamtopia Rainbow Magic Mermaid Doll has a rainbow-colored tail that lights up and changes color. She comes with a tiara and a brush.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1148	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm Remote Control Vehicle	The Hot Wheels Monster Trucks Live Megalodon Storm Remote Control Vehicle is a remote-controlled monster truck that looks like a giant shark. It has light-up eyes, chomping sounds, and a pivoting bite attack.	69.99	59.99	Hot Wheels	\N	\N	\N	Remote Control Vehicles	\N	\N
1149	\N	\N	LOL Surprise OMG Glamper Fashion Camper	The LOL Surprise OMG Glamper Fashion Camper is a playset that includes a camper, a pool, a slide, and accessories. It can hold up to 12 LOL Surprise dolls.	129.99	99.99	LOL Surprise	\N	\N	\N	Playsets	\N	\N
1150	\N	\N	LEGO Harry Potter Hogwarts Express Building Kit	The LEGO Harry Potter Hogwarts Express Building Kit is a 1,184-piece set that lets you build a detailed and iconic model of the Hogwarts Express from the Harry Potter movies.	149.99	129.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1151	\N	\N	Star Wars Millennium Falcon	Highly detailed replica of the iconic Star Wars spaceship, with lights and sounds.	49.99	39.99	Hasbro	\N	\N	\N	Toys	\N	\N
1152	\N	\N	LEGO Star Wars X-Wing Fighter	Buildable model of the classic Star Wars fighter, with opening wings and firing cannons.	29.99	24.99	LEGO	\N	\N	\N	Toys	\N	\N
1153	\N	\N	Hot Wheels Monster Trucks Mega Wrex	Giant monster truck with oversized tires and a roaring engine.	19.99	14.99	Mattel	\N	\N	\N	Toys	\N	\N
1154	\N	\N	Barbie Dreamhouse	Multi-story dollhouse with furniture, accessories, and a working elevator.	99.99	79.99	Mattel	\N	\N	\N	Toys	\N	\N
1155	\N	\N	Nerf Fortnite BASR-L Blaster	Toy blaster inspired by the popular video game, with a detachable scope and adjustable stock.	39.99	34.99	Hasbro	\N	\N	\N	Toys	\N	\N
1156	\N	\N	Minecraft Steve Action Figure	Highly detailed action figure of the iconic Minecraft character, with interchangeable accessories.	19.99	16.99	Mojang	\N	\N	\N	Toys	\N	\N
1157	\N	\N	Paw Patrol Ultimate Rescue Fire Truck	Large fire truck with lights, sounds, and a working water cannon.	49.99	39.99	Spin Master	\N	\N	\N	Toys	\N	\N
1158	\N	\N	L.O.L. Surprise! O.M.G. House of Surprises	Multi-story dollhouse with surprises hidden throughout, including dolls, accessories, and furniture.	109.99	89.99	MGA Entertainment	\N	\N	\N	Toys	\N	\N
1159	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Play-Doh ice cream truck with a variety of molds, tools, and accessories.	29.99	24.99	Hasbro	\N	\N	\N	Toys	\N	\N
1160	\N	\N	Crayola Washable Sidewalk Chalk	Pack of 12 vibrant sidewalk chalk sticks in assorted colors.	4.99	3.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1161	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Wooden doll with magnetic clothing and accessories for imaginative play.	19.99	16.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
1162	\N	\N	Beyblade Burst Surge Speedstorm Motor Strike Battle Set	Set of two Beyblade tops and a battling arena.	29.99	24.99	Hasbro	\N	\N	\N	Toys	\N	\N
1163	\N	\N	LEGO Friends Heartlake City Amusement Pier	Buildable amusement park with rides, games, and a Ferris wheel.	79.99	69.99	LEGO	\N	\N	\N	Toys	\N	\N
1164	\N	\N	Hot Wheels 5-Car Gift Pack	Pack of five assorted Hot Wheels cars.	14.99	11.99	Mattel	\N	\N	\N	Toys	\N	\N
1165	\N	\N	Nerf Rival Perses MXVIII-500 Blaster	High-powered toy blaster with a rotating barrel and a large magazine.	79.99	69.99	Hasbro	\N	\N	\N	Toys	\N	\N
1166	\N	\N	Minecraft Enchanted Sword Roleplay Toy	Foam sword shaped like the iconic Minecraft Enchanted Sword.	19.99	16.99	Mojang	\N	\N	\N	Toys	\N	\N
1167	\N	\N	Paw Patrol Lookout Tower Playset	Multi-level playset with a working elevator, lights, and sounds.	69.99	59.99	Spin Master	\N	\N	\N	Toys	\N	\N
1168	\N	\N	L.O.L. Surprise! Tweens Series 2 Fashion Doll	Fashion doll with interchangeable outfits, accessories, and a surprise reveal.	19.99	16.99	MGA Entertainment	\N	\N	\N	Toys	\N	\N
1169	\N	\N	Play-Doh Modeling Compound 10-Pack	Pack of ten 2-ounce containers of Play-Doh modeling compound in assorted colors.	9.99	7.99	Hasbro	\N	\N	\N	Toys	\N	\N
1170	\N	\N	Crayola Washable Markers 50-Count	Pack of 50 washable markers in assorted colors.	14.99	11.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1171	\N	\N	Melissa & Doug Wooden Shape Sorter Clock	Wooden shape sorter with a clock face and moving hands.	19.99	16.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
1172	\N	\N	Beyblade Burst QuadDrive Cosmic Vector Beystadium	Beystadium arena with a unique cosmic design.	29.99	24.99	Hasbro	\N	\N	\N	Toys	\N	\N
1173	\N	\N	LEGO Friends Olivias Flower Garden	Buildable flower garden with a greenhouse, pond, and a variety of flowers.	29.99	24.99	LEGO	\N	\N	\N	Toys	\N	\N
1174	\N	\N	Hot Wheels Monster Trucks Race Ace	Monster truck with a striking design and oversized tires.	14.99	11.99	Mattel	\N	\N	\N	Toys	\N	\N
1175	\N	\N	Nerf Elite 2.0 Commander RD-6 Blaster	Toy blaster with a rotating barrel, a detachable stock, and a 12-dart magazine.	29.99	24.99	Hasbro	\N	\N	\N	Toys	\N	\N
1176	\N	\N	Minecraft Creeper Plush	Soft and cuddly plush toy of the iconic Minecraft Creeper.	19.99	16.99	Mojang	\N	\N	\N	Toys	\N	\N
1177	\N	\N	Paw Patrol Chase's Police Cruiser	Toy police car with lights, sounds, and a working siren.	29.99	24.99	Spin Master	\N	\N	\N	Toys	\N	\N
1178	\N	\N	L.O.L. Surprise! OMG Sports Fashion Doll	Fashion doll with a sports-themed outfit and accessories.	24.99	19.99	MGA Entertainment	\N	\N	\N	Toys	\N	\N
1179	\N	\N	Play-Doh Kitchen Creations Ultimate Oven	Play-Doh oven with a variety of molds, tools, and accessories.	29.99	24.99	Hasbro	\N	\N	\N	Toys	\N	\N
1180	\N	\N	Crayola Washable Crayons 24-Count	Pack of 24 washable crayons in assorted colors.	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1181	\N	\N	Melissa & Doug Wooden Activity Table	Wooden activity table with a variety of hands-on activities.	99.99	79.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
1182	\N	\N	Beyblade Burst Surge Hypersphere Rip Fire Beystadium	Beystadium arena with a unique hypersphere design.	39.99	34.99	Hasbro	\N	\N	\N	Toys	\N	\N
1183	\N	\N	LEGO Friends Heartlake City Park	Buildable park with a slide, swing, and a variety of play areas.	49.99	39.99	LEGO	\N	\N	\N	Toys	\N	\N
1184	\N	\N	Hot Wheels Monster Trucks Tiger Shark	Monster truck with a tiger-themed design and oversized tires.	19.99	14.99	Mattel	\N	\N	\N	Toys	\N	\N
1185	\N	\N	Nerf Elite 2.0 Phoenix CS-6 Blaster	Toy blaster with a detachable stock, a 10-dart magazine, and a rapid-fire action.	39.99	34.99	Hasbro	\N	\N	\N	Toys	\N	\N
1186	\N	\N	Minecraft Diamond Sword Roleplay Toy	Foam sword shaped like the iconic Minecraft Diamond Sword.	19.99	16.99	Mojang	\N	\N	\N	Toys	\N	\N
1187	\N	\N	Toy Truck, Dump Truck	Large and sturdy dump truck with working dump bed.	39.99	29.99	Truck Zone	\N	\N	\N	Toy Trucks	\N	\N
1188	\N	\N	Toy Vehicle, Airplane	Large and detailed airplane model with lights and sound effects.	49.99	39.99	Aviation Wonders	\N	\N	\N	Toy Vehicles	\N	\N
1189	\N	\N	Star Wars: The Mandalorian - The Child Plush Toy	Standing at 11 inches tall, this adorable plush toy is an exact replica of the beloved character from the hit TV series, The Mandalorian. Made from high-quality materials, it features detailed stitching and soft, velvety fur. Perfect for cuddling, play, or display.	19.99	14.99	Disney	\N	\N	\N	Plush Toys	\N	\N
1190	\N	\N	LEGO Super Mario - Bowser's Castle Boss Battle Expansion Set	Take on the ultimate Super Mario boss battle with this exciting expansion set. Featuring a detailed Bowser figure, a rotating platform, and a POW Block launcher, kids can recreate the iconic castle battle from the Super Mario video games. Includes Mario and Bowser Jr. figures.	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1251	\N	\N	Weapon Toy, Plastic Bow and Arrow	Realistic plastic bow and arrow set with suction cup arrows.	29.99	24.99	Archery Zone	\N	\N	\N	Weapon Toys	\N	\N
1191	\N	\N	Barbie Dreamhouse Adventures Camper Van	Embark on endless adventures with the Barbie Dreamhouse Adventures Camper Van. This feature-packed vehicle transforms into a cozy camper with a kitchen, bathroom, bedroom, and even a slide-out pool. Includes Barbie doll, furniture, and accessories.	59.99	44.99	Barbie	\N	\N	\N	Dolls	\N	\N
1192	\N	\N	Nerf Fortnite BASR-L Blaster	Inspired by the popular video game, Fortnite, this Nerf blaster features a bolt-action mechanism and a removable magazine. Kids can launch darts up to 70 feet with pinpoint accuracy. Includes 6 Elite darts.	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
1193	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm	Get ready for monster truck mayhem with the Hot Wheels Monster Trucks Live Megalodon Storm. This remote-controlled truck features a unique shark-inspired design, oversized tires, and a chomping action. Includes a Hot Wheels car for crushing.	49.99	34.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
1194	\N	\N	Minecraft Dungeons Hero Edition	Explore the world of Minecraft Dungeons with the Hero Edition. This action-adventure game features a unique storyline, challenging dungeons, and a variety of weapons and artifacts. Includes the base game and the Hero Pass DLC.	29.99	19.99	Mojang	\N	\N	\N	Video Games	\N	\N
1195	\N	\N	Pokémon Sword and Shield Double Pack	Experience the latest Pokémon adventure with the Sword and Shield Double Pack. This bundle includes both versions of the game, allowing players to choose their own path and catch exclusive Pokémon. Includes two Nintendo Switch game cards.	99.99	79.99	Pokémon	\N	\N	\N	Video Games	\N	\N
1196	\N	\N	Beyblade Burst Surge Speedstorm Motor Strike Battle Set	Get ready for intense Beyblade battles with the Burst Surge Speedstorm Motor Strike Battle Set. This set includes two Beyblades, a Beystadium, and a launcher that boosts the Beyblades for incredible speed and power.	39.99	29.99	Beyblade	\N	\N	\N	Toys	\N	\N
1197	\N	\N	L.O.L. Surprise! OMG House of Surprises	Unbox the ultimate surprise with the L.O.L. Surprise! OMG House of Surprises. This giant dollhouse features 85 surprises, including furniture, accessories, and exclusive L.O.L. Surprise! dolls. Includes 4 dolls, a pet, and a car.	199.99	149.99	L.O.L. Surprise!	\N	\N	\N	Dolls	\N	\N
1198	\N	\N	Paw Patrol Mighty Lookout Tower	Join the Paw Patrol pups at the Mighty Lookout Tower. This interactive playset features a working elevator, a lookout deck, a zip line, and a launcher for the included vehicles. Includes 6 Paw Patrol figures and 3 vehicles.	89.99	64.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
1199	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Get creative with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck. This pretend playset features a working ice cream machine, a variety of toppings, and molds to create colorful ice cream treats. Includes 5 cans of Play-Doh.	29.99	19.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
1200	\N	\N	Hatchimals Pixies Crystal Flyers Rainbow Glitter Fairy	Take flight with the Hatchimals Pixies Crystal Flyers Rainbow Glitter Fairy. This magical creature has iridescent wings that shimmer and flutter when it flies. Includes a display stand and a collector's card.	14.99	9.99	Hatchimals	\N	\N	\N	Toys	\N	\N
1201	\N	\N	Ryan's World Giant Mystery Egg	Unleash the ultimate surprise with the Ryan's World Giant Mystery Egg. This colossal egg contains over 50 surprises, including toys, slime, and collectibles from Ryan's World. Perfect for unboxing fun and excitement.	49.99	34.99	Ryan's World	\N	\N	\N	Toys	\N	\N
1202	\N	\N	Barbie Extra Doll #15	Celebrate individuality with the Barbie Extra Doll #15. This fashion-forward doll features a unique style with bright colors, bold patterns, and over-the-top accessories. Includes a doll, outfit, and accessories.	24.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
1203	\N	\N	Hot Wheels Criss Cross Crash Track Set	Get ready for high-speed action with the Hot Wheels Criss Cross Crash Track Set. This multi-level track features intersecting loops, ramps, and a crash zone. Includes two Hot Wheels cars for thrilling races and stunts.	49.99	39.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
1204	\N	\N	Nerf Fortnite Pump SG Shotgun	Experience the Fortnite fun in real life with the Nerf Fortnite Pump SG Shotgun. This pump-action blaster features a realistic design and fires Mega darts up to 27 feet. Includes 4 Mega darts.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
1205	\N	\N	LEGO Star Wars The Razor Crest Microfighter	Build and play with the iconic Razor Crest ship from The Mandalorian TV series with the LEGO Star Wars The Razor Crest Microfighter. This compact set features a detailed design, rotating cannons, and a minifigure of The Mandalorian.	9.99	7.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1206	\N	\N	Minecraft Dungeons Jungle Awakens DLC	Expand your Minecraft Dungeons adventure with the Jungle Awakens DLC. Explore a new jungle biome, battle new enemies, and uncover hidden treasures. Includes new weapons, armor, and artifacts.	19.99	14.99	Mojang	\N	\N	\N	Video Games	\N	\N
1207	\N	\N	Barbie Fashionistas Ultimate Closet	Create endless fashion possibilities with the Barbie Fashionistas Ultimate Closet. This accessory set includes over 50 pieces, including clothes, shoes, accessories, and a doll stand. Perfect for fashion-loving kids.	29.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
1208	\N	\N	Hot Wheels Bone Shaker Monster Truck	Get ready for monstrous fun with the Hot Wheels Bone Shaker Monster Truck. This oversized truck features a unique skeleton design, oversized tires, and a pull-back motor. Includes a Hot Wheels car for crushing.	29.99	24.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
1209	\N	\N	Nerf Alpha Strike Fang QS-4 Blaster	Experience fast-paced action with the Nerf Alpha Strike Fang QS-4 Blaster. This semi-automatic blaster fires 4 darts in rapid succession with just a pull of the trigger. Includes 8 Elite darts.	14.99	9.99	Nerf	\N	\N	\N	Blasters	\N	\N
1210	\N	\N	LEGO Harry Potter Hogwarts Castle	Build and explore the iconic Hogwarts Castle from the Harry Potter movies with the LEGO Harry Potter Hogwarts Castle. This massive set features over 6,000 pieces, 27 microfigures, and countless magical details.	399.99	299.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1211	\N	\N	Barbie Cutie Reveal Chelsea Doll	Unbox a world of cuteness with the Barbie Cutie Reveal Chelsea Doll. Each doll comes in a soft animal-shaped costume that transforms into a fabulous outfit with a pull of the string. Includes a doll, outfit, accessories, and a pet.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1212	\N	\N	Hot Wheels Mario Kart Luigi Circuit Track Set	Race into the world of Mario Kart with the Hot Wheels Mario Kart Luigi Circuit Track Set. This track set features a loop, a jump, and a finish line inspired by the iconic Luigi Circuit course. Includes a Mario Kart Luigi die-cast car.	29.99	24.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
1213	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	Experience the Fortnite fun in real life with the Nerf Fortnite SP-L Elite Dart Blaster. This compact blaster features a pump-action mechanism and fires Elite darts up to 27 feet. Includes 3 Elite darts.	14.99	9.99	Nerf	\N	\N	\N	Blasters	\N	\N
1252	\N	\N	Nerf Fortnite BASR-L Blaster	Full-auto, clip-fed, Fortnite-themed blaster for kids, teens, and adults. Fires Elite darts up to 80 feet per second. Includes 6-dart clip and 20 Elite darts. For ages 8 and up.	29.99	24.99	Nerf	\N	\N	\N	Toy gun	\N	\N
1214	\N	\N	LEGO Star Wars AT-AT Walker	Build and play with the iconic AT-AT Walker from Star Wars: The Empire Strikes Back with the LEGO Star Wars AT-AT Walker. This detailed set features a rotating cannon, a cockpit, and space for up to 4 minifigures.	159.99	119.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1215	\N	\N	Barbie Dreamtopia Rainbow Cove Unicorn	Enter the magical world of Dreamtopia with the Barbie Dreamtopia Rainbow Cove Unicorn. This enchanting creature features a rainbow mane and tail, a shimmering horn, and a sparkling body. Includes a doll stand.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1216	\N	\N	Hot Wheels Monster Trucks Demolition Doubles	Get ready for double the destruction with the Hot Wheels Monster Trucks Demolition Doubles. This set includes two monster trucks that can be combined to create a giant vehicle. Features oversized tires, unique designs, and pull-back motors.	29.99	24.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
1217	\N	\N	Nerf Fortnite Recon CS-6 Dart Blaster	Experience the Fortnite fun in real life with the Nerf Fortnite Recon CS-6 Dart Blaster. This clip-fed blaster features a rotating barrel and fires Elite darts up to 27 feet. Includes a 6-dart clip and 6 Elite darts.	19.99	14.99	Nerf	\N	\N	\N	Blasters	\N	\N
1218	\N	\N	LEGO Marvel Avengers Avengers Tower Battle	Build and defend the iconic Avengers Tower with the LEGO Marvel Avengers Avengers Tower Battle. This action-packed set features a detailed tower, a Helicarrier, and minifigures of Iron Man, Captain America, Thor, and Loki.	99.99	79.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1219	\N	\N	Barbie Made to Move Doll	Move with Barbie and express yourself with the Barbie Made to Move Doll. This doll features 22 points of articulation, allowing for endless poses and movements. Includes a doll and a stand.	24.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
1220	\N	\N	Hot Wheels Color Shifters 5-Car Pack	Experience the magic of color-changing cars with the Hot Wheels Color Shifters 5-Car Pack. Each car transforms its color when immersed in cold water. Includes 5 different Hot Wheels cars.	14.99	9.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1221	\N	\N	Nerf Minecraft Warden Blaster	Bring the Minecraft world to life with the Nerf Minecraft Warden Blaster. This foam dart blaster features a rotating barrel and fires up to 3 darts at once. Includes 10 foam darts.	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
1222	\N	\N	Action Figure, Superhero with Accessories	Highly detailed action figure with multiple points of articulation, comes with weapons and gadgets.	19.99	14.99	Superhero Corp	\N	\N	\N	Action Figures	\N	\N
1223	\N	\N	Board Game, Strategy Game for 2-4 Players	Fast-paced strategy game with unique mechanics, perfect for family game nights.	24.99	19.99	Game Masters Inc	\N	\N	\N	Board Games	\N	\N
1224	\N	\N	Building Blocks, Creative Construction Set	Large set of colorful building blocks, encourages creativity and imagination.	29.99	24.99	Block Builders	\N	\N	\N	Building Toys	\N	\N
1225	\N	\N	Card Game, Collectible Trading Card Game	Popular trading card game with unique characters and abilities.	14.99	11.99	Card Masters	\N	\N	\N	Card Games	\N	\N
1226	\N	\N	Craft Kit, Slime Making Kit	All-inclusive kit for making your own fluffy and colorful slime.	19.99	16.99	Craft Central	\N	\N	\N	Arts & Crafts	\N	\N
1227	\N	\N	Doll, Interactive Fashion Doll with Accessories	Posable fashion doll with multiple outfits and accessories.	24.99	19.99	Dollhouse Divas	\N	\N	\N	Dolls	\N	\N
1228	\N	\N	Educational Toy, STEM Learning Kit	Hands-on kit that teaches basic science, technology, engineering, and math concepts.	39.99	29.99	STEM Solutions	\N	\N	\N	Educational Toys	\N	\N
1229	\N	\N	Electronic Toy, Remote Control Car	High-speed remote control car with multiple functions and rechargeable battery.	49.99	39.99	Speed Racers	\N	\N	\N	Electronic Toys	\N	\N
1230	\N	\N	Figure Set, Animal Figurines	Set of realistic animal figurines, perfect for imaginative play.	19.99	14.99	Wildlife Wonders	\N	\N	\N	Figurines	\N	\N
1231	\N	\N	Game Console, Portable Video Game System	Compact and powerful portable video game system with a large library of games.	149.99	119.99	Game Zone	\N	\N	\N	Video Games	\N	\N
1232	\N	\N	Interactive Toy, Talking Robot	Cute and interactive robot that responds to voice commands and performs tricks.	39.99	29.99	Toytronics	\N	\N	\N	Interactive Toys	\N	\N
1233	\N	\N	Musical Instrument, Kids Drum Set	Complete drum set with drumsticks and stool, perfect for aspiring musicians.	59.99	49.99	Music Makers	\N	\N	\N	Musical Instruments	\N	\N
1234	\N	\N	Outdoor Toy, Trampoline	Large and sturdy trampoline with safety net, provides hours of outdoor fun.	199.99	149.99	Jumpers Inc	\N	\N	\N	Outdoor Toys	\N	\N
1235	\N	\N	Party Game, Pinata	Colorful and festive pinata filled with candy or small toys.	14.99	11.99	Party Central	\N	\N	\N	Party Supplies	\N	\N
1236	\N	\N	Puzzle, 3D Jigsaw Puzzle	Challenging and rewarding 3D jigsaw puzzle with intricate design.	24.99	19.99	Puzzle Masters	\N	\N	\N	Puzzles	\N	\N
1237	\N	\N	Science Kit, Chemistry Experiment Kit	Comprehensive kit for conducting safe and exciting chemistry experiments.	39.99	29.99	Science Explorers	\N	\N	\N	Science Kits	\N	\N
1238	\N	\N	Scooter, Razor Scooter	Durable and lightweight scooter with adjustable handlebars and easy-to-fold design.	99.99	79.99	Razor Scooters	\N	\N	\N	Ride-On Toys	\N	\N
1239	\N	\N	Sports Toy, Basketball Hoop Set	Portable basketball hoop set with adjustable height and breakaway rim.	49.99	39.99	Hoop Stars	\N	\N	\N	Sports Toys	\N	\N
1240	\N	\N	Stuffed Animal, Giant Teddy Bear	Extra-large and cuddly teddy bear, perfect for bedtime cuddles.	49.99	39.99	Teddy Bear Factory	\N	\N	\N	Stuffed Animals	\N	\N
1241	\N	\N	Toy Car, Remote Control Monster Truck	Rugged and powerful remote control monster truck with oversize wheels.	39.99	29.99	Wild Racers	\N	\N	\N	Toy Cars	\N	\N
1242	\N	\N	Toy Gun, Nerf Blaster	High-powered Nerf blaster with interchangeable accessories.	29.99	24.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
1243	\N	\N	Toy House, Dollhouse with Furniture	Spacious dollhouse with multiple rooms and furniture pieces.	49.99	39.99	Dollhouse Dreams	\N	\N	\N	Toy Houses	\N	\N
1244	\N	\N	Toy Kitchen, Play Kitchen Set	Realistic play kitchen set with pretend appliances and accessories.	59.99	49.99	Kiddie Kitchens	\N	\N	\N	Toy Kitchens	\N	\N
1245	\N	\N	Toy Microphone, Karaoke Machine	Portable karaoke machine with microphone, music effects, and built-in speaker.	39.99	29.99	Sing Stars	\N	\N	\N	Toy Musical Instruments	\N	\N
1246	\N	\N	Video Game, Action-Adventure Game	Epic action-adventure game with stunning graphics and immersive gameplay.	59.99	49.99	Game Masters Inc	\N	\N	\N	Video Games	\N	\N
1247	\N	\N	Video Game, Sports Game	Realistic and exciting sports game with multiple game modes and teams.	39.99	29.99	Sports Zone	\N	\N	\N	Video Games	\N	\N
1248	\N	\N	Water Toy, Inflatable Pool	Large and durable inflatable pool, perfect for summer fun.	79.99	59.99	Pool Paradise	\N	\N	\N	Water Toys	\N	\N
1249	\N	\N	Water Toy, Squirt Gun	Powerful and long-range squirt gun with adjustable nozzle.	14.99	11.99	Water Warriors	\N	\N	\N	Water Toys	\N	\N
1250	\N	\N	Weapon Toy, Foam Sword	Safe and durable foam sword, perfect for imaginative play.	19.99	14.99	Foam Fighters	\N	\N	\N	Weapon Toys	\N	\N
1253	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	With this Play-Doh ice cream truck playset, kids can pretend to run their own ice cream business and create all kinds of colorful and creative frozen treats.	29.99	24.99	Play-Doh	\N	\N	\N	Arts and crafts	\N	\N
1254	\N	\N	Nintendo Switch Lite	Nintendo Switch Lite is a compact, portable version of the Nintendo Switch system. It's perfect for on-the-go gaming and is also great for multiplayer gaming with friends and family.	199.99	179.99	Nintendo	\N	\N	\N	Video game	\N	\N
1255	\N	\N	LEGO Star Wars: The Rise of Skywalker Millennium Falcon	The LEGO Star Wars: The Rise of Skywalker Millennium Falcon is a buildable model of the iconic spaceship from the Star Wars movies. It features rotating laser cannons, a lowering ramp, and a detailed interior.	169.99	149.99	LEGO	\N	\N	\N	Building toy	\N	\N
1256	\N	\N	Barbie Dreamhouse	The Barbie Dreamhouse is a classic dollhouse that has been a favorite of children for generations. It features three stories, eight rooms, and a working elevator.	199.99	179.99	Barbie	\N	\N	\N	Dollhouse	\N	\N
1257	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Kit	The Hot Wheels Track Builder Unlimited Triple Loop Kit is a set of track pieces that can be used to create a variety of different track layouts. It includes three loops, two launchers, and a variety of other track pieces.	29.99	24.99	Hot Wheels	\N	\N	\N	Toy car	\N	\N
1258	\N	\N	L.O.L. Surprise! O.M.G. House of Surprises	The L.O.L. Surprise! O.M.G. House of Surprises is a large dollhouse that comes with 85 surprises. It features three floors, six rooms, and a working elevator.	199.99	179.99	L.O.L. Surprise!	\N	\N	\N	Dollhouse	\N	\N
1259	\N	\N	Razor E100 Electric Scooter	The Razor E100 Electric Scooter is a fun and easy way for kids to get around. It features a 100-watt motor, a top speed of 10 mph, and a range of up to 10 miles.	199.99	179.99	Razor	\N	\N	\N	Ride-on toy	\N	\N
1260	\N	\N	Melissa & Doug Wooden Activity Table with Building Blocks	The Melissa & Doug Wooden Activity Table with Building Blocks is a great way for kids to learn and play. It features a variety of activities, including building blocks, a chalkboard, and a sandpit.	99.99	89.99	Melissa & Doug	\N	\N	\N	Educational toy	\N	\N
1261	\N	\N	Crayola Ultimate Crayon Collection	The Crayola Ultimate Crayon Collection is a set of 150 crayons in a variety of colors. It's perfect for kids who love to draw and color.	49.99	39.99	Crayola	\N	\N	\N	Arts and crafts	\N	\N
1262	\N	\N	LEGO Minecraft The Ender Dragon	The LEGO Minecraft The Ender Dragon is a buildable model of the iconic boss mob from the Minecraft video game. It features movable wings, a fire-breathing mouth, and a detailed base.	49.99	39.99	LEGO	\N	\N	\N	Building toy	\N	\N
1263	\N	\N	Nerf Fortnite SP-L	The Nerf Fortnite SP-L is a compact, single-shot blaster that's perfect for on-the-go play. It fires Elite darts up to 75 feet per second and includes 3 Elite darts.	14.99	12.99	Nerf	\N	\N	\N	Toy gun	\N	\N
1264	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Playset	With this Play-Doh ice cream truck playset, kids can pretend to run their own ice cream business and create all kinds of colorful and creative frozen treats.	29.99	24.99	Play-Doh	\N	\N	\N	Arts and crafts	\N	\N
1265	\N	\N	Nintendo Switch Lite	Nintendo Switch Lite is a compact, portable version of the Nintendo Switch system. It's perfect for on-the-go gaming and is also great for multiplayer gaming with friends and family.	199.99	179.99	Nintendo	\N	\N	\N	Video game	\N	\N
1266	\N	\N	LEGO Star Wars: The Rise of Skywalker Millennium Falcon	The LEGO Star Wars: The Rise of Skywalker Millennium Falcon is a buildable model of the iconic spaceship from the Star Wars movies. It features rotating laser cannons, a lowering ramp, and a detailed interior.	169.99	149.99	LEGO	\N	\N	\N	Building toy	\N	\N
1267	\N	\N	Barbie Dreamhouse	The Barbie Dreamhouse is a classic dollhouse that has been a favorite of children for generations. It features three stories, eight rooms, and a working elevator.	199.99	179.99	Barbie	\N	\N	\N	Dollhouse	\N	\N
1268	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Kit	The Hot Wheels Track Builder Unlimited Triple Loop Kit is a set of track pieces that can be used to create a variety of different track layouts. It includes three loops, two launchers, and a variety of other track pieces.	29.99	24.99	Hot Wheels	\N	\N	\N	Toy car	\N	\N
1269	\N	\N	L.O.L. Surprise! O.M.G. House of Surprises	The L.O.L. Surprise! O.M.G. House of Surprises is a large dollhouse that comes with 85 surprises. It features three floors, six rooms, and a working elevator.	199.99	179.99	L.O.L. Surprise!	\N	\N	\N	Dollhouse	\N	\N
1270	\N	\N	Razor E100 Electric Scooter	The Razor E100 Electric Scooter is a fun and easy way for kids to get around. It features a 100-watt motor, a top speed of 10 mph, and a range of up to 10 miles.	199.99	179.99	Razor	\N	\N	\N	Ride-on toy	\N	\N
1271	\N	\N	Melissa & Doug Wooden Activity Table with Building Blocks	The Melissa & Doug Wooden Activity Table with Building Blocks is a great way for kids to learn and play. It features a variety of activities, including building blocks, a chalkboard, and a sandpit.	99.99	89.99	Melissa & Doug	\N	\N	\N	Educational toy	\N	\N
1272	\N	\N	Crayola Ultimate Crayon Collection	The Crayola Ultimate Crayon Collection is a set of 150 crayons in a variety of colors. It's perfect for kids who love to draw and color.	49.99	39.99	Crayola	\N	\N	\N	Arts and crafts	\N	\N
1273	\N	\N	LEGO Minecraft The Ender Dragon	The LEGO Minecraft The Ender Dragon is a buildable model of the iconic boss mob from the Minecraft video game. It features movable wings, a fire-breathing mouth, and a detailed base.	49.99	39.99	LEGO	\N	\N	\N	Building toy	\N	\N
1274	\N	\N	Nerf Fortnite SP-L	The Nerf Fortnite SP-L is a compact, single-shot blaster that's perfect for on-the-go play. It fires Elite darts up to 75 feet per second and includes 3 Elite darts.	14.99	12.99	Nerf	\N	\N	\N	Toy gun	\N	\N
1275	\N	\N	Baby Monitor	Baby monitor with video and audio capabilities	40.00	32.00	VTech	\N	\N	\N	Baby Monitors	\N	\N
1276	\N	\N	Remote Control Monster Truck	1:10 scale remote control monster truck with working headlights and taillights. Top speed of 20 mph.	299.99	249.99	Redcat	\N	\N	\N	Vehicles	\N	\N
1277	\N	\N	Nerf Fortnite BASR-L Blaster	Full-size replica of the Fortnite BASR-L blaster. Shoots foam darts up to 75 feet.	49.99	39.99	Nerf	\N	\N	\N	Weapons	\N	\N
1278	\N	\N	LEGO Star Wars: The Mandalorian's Razor Crest	75292-piece LEGO set of the Razor Crest spaceship from The Mandalorian. Includes minifigures of Din Djarin, Grogu, and Kuiil.	129.99	99.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1279	\N	\N	Barbie Dreamhouse Playset	Three-story Barbie dollhouse with over 70 accessories. Includes furniture, a pool, and a garage.	299.99	199.99	Barbie	\N	\N	\N	Dolls	\N	\N
1280	\N	\N	Hot Wheels Track Builder Unlimited Corkscrew Crash Track Set	Track set with a motorized corkscrew loop and multiple crash zones. Includes two Hot Wheels cars.	49.99	39.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1281	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Play-Doh ice cream truck playset with over 20 tools and accessories. Includes molds to create different ice cream shapes.	29.99	19.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1282	\N	\N	Melissa & Doug Zoo Animal Magnetic Dress-Up Set	Magnetic dress-up set with 10 wooden zoo animals and over 50 magnetic clothing pieces.	24.99	19.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
1283	\N	\N	Crayola Super Tips Washable Markers, 100 Count	Pack of 100 washable markers in a variety of colors. Includes a carrying case.	29.99	19.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1284	\N	\N	Nintendo Switch Lite	Handheld gaming console that plays all Nintendo Switch games. Available in multiple colors.	199.99	179.99	Nintendo	\N	\N	\N	Electronics	\N	\N
1285	\N	\N	Air Hogs Supernova Gravity Defying Stunt Drone	Stunt drone that can fly in all directions and perform flips and rolls. Includes a remote control.	79.99	59.99	Air Hogs	\N	\N	\N	Vehicles	\N	\N
1286	\N	\N	LEGO Minecraft: The End Battle	238-piece LEGO set of the End Battle from Minecraft. Includes minifigures of the Dragon Ender, Steve, and Alex.	29.99	19.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1287	\N	\N	VTech KidiZoom Smartwatch DX2	Smartwatch for kids with a camera, games, and a pedometer. Available in multiple colors.	59.99	49.99	VTech	\N	\N	\N	Electronics	\N	\N
1288	\N	\N	Beyblade Burst Surge Hypersphere Vertical Drop Battle Set	Beyblade Burst set with a vertical drop battle arena and two Beyblades.	29.99	19.99	Beyblade Burst	\N	\N	\N	Toys & Games	\N	\N
1289	\N	\N	Paw Patrol: The Movie Ultimate City Tower Playset	Three-story Paw Patrol playset with over 60 pieces. Includes a working elevator, a lookout tower, and a vehicle launcher.	99.99	79.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
1290	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	Pump-action blaster that shoots Fortnite Elite darts. Includes a 10-dart clip.	29.99	19.99	Nerf	\N	\N	\N	Weapons	\N	\N
1291	\N	\N	LEGO Harry Potter: Hogwarts Castle	6020-piece LEGO set of Hogwarts Castle from the Harry Potter series. Includes minifigures of Harry Potter, Ron Weasley, and Hermione Granger.	399.99	299.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1292	\N	\N	Barbie Fashionistas Ultimate Closet	Barbie doll closet with over 50 fashion pieces. Includes clothes, shoes, and accessories.	59.99	39.99	Barbie	\N	\N	\N	Dolls	\N	\N
1293	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm Playset	Hot Wheels playset with a giant Megalodon monster truck that eats and launches cars. Includes two Hot Wheels monster trucks.	79.99	59.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1294	\N	\N	Crayola Twistables Crayons, 50 Count	Pack of 50 twistable crayons in a variety of colors. Includes a carrying case.	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1295	\N	\N	Toy Car	Red toy car with working wheels and doors	10.00	8.00	Hot Wheels	\N	\N	\N	Cars	\N	\N
1296	\N	\N	Doll	Soft and cuddly doll with long hair and pretty dress	15.00	12.00	Barbie	\N	\N	\N	Dolls	\N	\N
1297	\N	\N	Building Blocks	Colorful building blocks with different shapes and sizes	20.00	16.00	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1298	\N	\N	Train Set	Wooden train set with tracks, trains, and accessories	30.00	24.00	Thomas & Friends	\N	\N	\N	Train Sets	\N	\N
1299	\N	\N	Play Kitchen	Fully equipped play kitchen with stove, oven, sink, and play food	40.00	32.00	Step2	\N	\N	\N	Play Kitchens	\N	\N
1300	\N	\N	Activity Cube	Interactive activity cube with lights, sounds, and different activities	25.00	20.00	VTech	\N	\N	\N	Activity Toys	\N	\N
1301	\N	\N	Puzzle	Simple puzzle with large pieces and bright colors	12.00	9.00	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
1302	\N	\N	Board Game	Classic board game for 2-4 players	20.00	16.00	Monopoly	\N	\N	\N	Board Games	\N	\N
1303	\N	\N	Art Supplies	Box of crayons, markers, and paper	15.00	12.00	Crayola	\N	\N	\N	Art Supplies	\N	\N
1304	\N	\N	Musical Instrument	Toy piano with 8 keys and different sounds	20.00	16.00	Fisher-Price	\N	\N	\N	Musical Toys	\N	\N
1305	\N	\N	Stuffed Animal	Soft and cuddly stuffed giraffe	18.00	14.00	Gund	\N	\N	\N	Stuffed Animals	\N	\N
1306	\N	\N	Playhouse	Small playhouse with door, windows, and roof	50.00	40.00	Little Tikes	\N	\N	\N	Playhouses	\N	\N
1307	\N	\N	Slime	Colorful and stretchy slime in a container	10.00	8.00	Elmer's	\N	\N	\N	Slime	\N	\N
1308	\N	\N	Science Kit	Educational science kit with experiments and activities	25.00	20.00	National Geographic	\N	\N	\N	Science Kits	\N	\N
1309	\N	\N	Video Game	Educational video game for kids	20.00	16.00	PBS Kids	\N	\N	\N	Video Games	\N	\N
1310	\N	\N	Book	Interactive book with flaps, pop-ups, and sounds	15.00	12.00	Usborne Books	\N	\N	\N	Books	\N	\N
1311	\N	\N	Bath Toys	Set of rubber duckies and other bath toys	12.00	9.00	Munchkin	\N	\N	\N	Bath Toys	\N	\N
1312	\N	\N	Ride-On Toy	Small ride-on car with steering wheel and pedals	40.00	32.00	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
1313	\N	\N	Toy Tool Set	Toy tool set with hammer, wrench, and screwdriver	18.00	14.00	Melissa & Doug	\N	\N	\N	Toy Tools	\N	\N
1314	\N	\N	Dress-Up Clothes	Box of dress-up clothes with hats, scarves, and jewelry	20.00	16.00	Melissa & Doug	\N	\N	\N	Dress-Up Clothes	\N	\N
1315	\N	\N	Play Mat	Soft and colorful play mat with different textures and activities	25.00	20.00	Tiny Love	\N	\N	\N	Play Mats	\N	\N
1316	\N	\N	Baby Doll	Realistic baby doll with feeding bottle and accessories	30.00	24.00	Corolle	\N	\N	\N	Baby Dolls	\N	\N
1317	\N	\N	Blanket	Soft and cuddly blanket with cute animal design	20.00	16.00	Little Giraffe	\N	\N	\N	Blankets	\N	\N
1318	\N	\N	Teether	Teething toy made of soft silicone	10.00	8.00	Nuby	\N	\N	\N	Teethers	\N	\N
1319	\N	\N	Rattle	Rattle with colorful beads and a bell	12.00	9.00	Skip Hop	\N	\N	\N	Rattles	\N	\N
1320	\N	\N	Pacifier	Pacifier with a orthodontic nipple	10.00	8.00	MAM	\N	\N	\N	Pacifiers	\N	\N
1321	\N	\N	Changing Pad	Changing pad with raised edges for safety	15.00	12.00	Summer Infant	\N	\N	\N	Changing Pads	\N	\N
1322	\N	\N	Diaper Bag	Stylish diaper bag with multiple compartments and pockets	30.00	24.00	Skip Hop	\N	\N	\N	Diaper Bags	\N	\N
1323	\N	\N	Changing Table	Changing table with a removable changing tray	75.00	60.00	Delta Children	\N	\N	\N	Changing Tables	\N	\N
1324	\N	\N	Fire Engine	Detailed fire engine with lights and sounds, extendable ladder, and water cannon.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1325	\N	\N	Paw Patrol Lookout Tower	Interactive playset with lights, sounds, and multiple levels.	39.99	29.99	Spin Master	\N	\N	\N	Action Figures	\N	\N
1326	\N	\N	My Little Pony Rainbow Dash	Colorful and detailed pony figure with wings and a flowing mane.	14.99	9.99	Hasbro	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1327	\N	\N	Nerf Ultra Strike	High-powered blaster with long-range accuracy.	29.99	24.99	Hasbro	\N	\N	\N	Outdoor Toys	\N	\N
1328	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Play kitchen set with ice cream machine, molds, and accessories.	34.99	24.99	Hasbro	\N	\N	\N	Playsets	\N	\N
1329	\N	\N	Barbie Dreamhouse	Spacious dollhouse with multiple rooms, furniture, and accessories.	99.99	79.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1330	\N	\N	Hot Wheels 50-Car Pack	Assortment of 50 Hot Wheels die-cast cars.	24.99	19.99	Mattel	\N	\N	\N	Die-Cast Vehicles	\N	\N
1331	\N	\N	Mega Construx Halo UNSC Warthog	Buildable Halo vehicle with rolling wheels and multiple figures.	29.99	24.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1332	\N	\N	Crayola Super Tips Washable Markers	Set of 100 washable markers in various colors.	14.99	9.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1333	\N	\N	LEGO Star Wars The Mandalorian's N-1 Starfighter	Buildable Star Wars spaceship with minifigures of The Mandalorian and Grogu.	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1334	\N	\N	Hatchimals Pixies Crystal Flyers Rainbow Glitter Fairy	Interactive fairy doll that flies with motion and lights.	29.99	24.99	Spin Master	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1335	\N	\N	Playmobil Police Station	Multi-level playset with multiple rooms, figures, and accessories.	49.99	39.99	Playmobil	\N	\N	\N	Playsets	\N	\N
1336	\N	\N	Nerf Fortnite BASR-L Blaster	Replica of Fortnite blaster with detachable scope.	39.99	29.99	Hasbro	\N	\N	\N	Outdoor Toys	\N	\N
1337	\N	\N	Barbie Color Reveal Chelsea Doll	Mystery doll with color-changing reveal and multiple accessories.	9.99	6.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1338	\N	\N	Play-Doh Kitchen Creations Grill 'N Stamp Playset	Interactive playset for creating and grilling pretend food.	19.99	14.99	Hasbro	\N	\N	\N	Playsets	\N	\N
1339	\N	\N	Hot Wheels Monster Trucks 5-Alarm	Monster truck with oversized wheels and detailed design.	14.99	9.99	Mattel	\N	\N	\N	Die-Cast Vehicles	\N	\N
1340	\N	\N	Mega Construx American Girl Truly Me Pizza Party	Buildable American Girl pizza party playset with figures and accessories.	34.99	29.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1341	\N	\N	Barbie Dreamtopia Chelsea Mermaid Doll	Mermaid doll with colorful tail and tiara.	14.99	9.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1342	\N	\N	Playmobil Dino Rise Triceratops	Buildable Triceratops dinosaur with moving parts and sound effects.	24.99	19.99	Playmobil	\N	\N	\N	Building Toys	\N	\N
1343	\N	\N	Crayola Scribble Scrubbie Pets Mermaid Lagoon Playset	Interactive playset for washing and recoloring pet figurines.	19.99	14.99	Crayola	\N	\N	\N	Playsets	\N	\N
1344	\N	\N	LEGO City Police Station	Large-scale police station playset with multiple rooms, vehicles, and figures.	99.99	79.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1345	\N	\N	Hatchimals Surprise	Hatching egg with a collectible creature inside.	19.99	14.99	Spin Master	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1346	\N	\N	Play-Doh Slime Super Color Change Bucket	Bucket of color-changing slime for sensory play.	14.99	9.99	Hasbro	\N	\N	\N	Arts and Crafts	\N	\N
1347	\N	\N	Barbie Dreamhouse Adventures DreamPlane	Convertible airplane playset with multiple rooms and accessories.	49.99	39.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1348	\N	\N	Hot Wheels Monster Trucks Megalodon	Monster truck shaped like a shark with oversized wheels.	24.99	19.99	Mattel	\N	\N	\N	Die-Cast Vehicles	\N	\N
1349	\N	\N	LEGO Star Wars The Child	Buildable Yoda-like creature from The Mandalorian series.	19.99	14.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1350	\N	\N	Crayola Color Wonder Mess Free Coloring Pages	Book of mess-free coloring pages with special markers that only work on the pages.	14.99	9.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1351	\N	\N	Barbie Dreamtopia Rainbow Magic Pegasus	Colorful pegasus doll with flowing mane and tail.	24.99	19.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1352	\N	\N	Play-Doh Kitchen Creations Rainbow Kitchen	Play kitchen set with multiple appliances, molds, and accessories.	29.99	24.99	Hasbro	\N	\N	\N	Playsets	\N	\N
1353	\N	\N	Hot Wheels City Ultimate Garage	Multi-level garage playset with ramps, elevators, and multiple parking spaces.	199.99	99.99	Mattel	\N	\N	\N	Die-Cast Vehicles	\N	\N
1354	\N	\N	LEGO Minecraft The Nether Fortress	Buildable Minecraft fortress playset with multiple characters and features.	79.99	69.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1355	\N	\N	Crayola Super Tips Washable Markers, 20-Count	Set of 20 washable markers in various colors.	9.99	6.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1356	\N	\N	Barbie Fashionistas Doll with Wheelchair	Fashion doll with removable wheelchair and accessories.	19.99	14.99	Mattel	\N	\N	\N	Dolls and Stuffed Animals	\N	\N
1357	\N	\N	Playmobil My Take Along Pirate Ship Playset	Portable pirate ship playset with figures and accessories.	29.99	24.99	Playmobil	\N	\N	\N	Playsets	\N	\N
1358	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Kit	Track building system with loops, curves, and jumps.	29.99	24.99	Mattel	\N	\N	\N	Die-Cast Vehicles	\N	\N
1359	\N	\N	LEGO Friends Heartlake City School	Multi-level school building playset with multiple rooms, characters, and features.	99.99	79.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1360	\N	\N	Toy Car	Red toy car with realistic details and working wheels	4.99	3.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1361	\N	\N	Action Figure	Superhero action figure with movable joints and accessories	9.99	7.99	Marvel	\N	\N	\N	Superheroes	\N	\N
1362	\N	\N	Dollhouse	Pink and white dollhouse with furniture and accessories	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1363	\N	\N	Building Blocks	Set of colorful building blocks in various shapes and sizes	14.99	10.99	Mega Bloks	\N	\N	\N	Construction	\N	\N
1364	\N	\N	Board Game	Classic board game for 2-4 players	19.99	14.99	Monopoly	\N	\N	\N	Games	\N	\N
1365	\N	\N	Stuffed Animal	Soft and cuddly stuffed teddy bear	9.99	7.99	Teddy Bear	\N	\N	\N	Animals	\N	\N
1366	\N	\N	Craft Kit	Art and craft kit with supplies for painting, drawing, and sculpting	14.99	10.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1367	\N	\N	Puzzle	100-piece jigsaw puzzle with a colorful animal scene	9.99	7.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1368	\N	\N	Play Kitchen	Pink play kitchen with realistic appliances and accessories	29.99	21.99	Little Tikes	\N	\N	\N	Pretend Play	\N	\N
1369	\N	\N	Tea Set	Tea set with teapot, cups, and saucers for pretend play	14.99	10.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
1370	\N	\N	Train Set	Electric train set with tracks, train cars, and accessories	39.99	29.99	Thomas & Friends	\N	\N	\N	Trains	\N	\N
1371	\N	\N	Scooter	Red and black scooter with adjustable handlebars and a kickstand	39.99	29.99	Razor	\N	\N	\N	Ride-Ons	\N	\N
1372	\N	\N	Tricycle	Blue tricycle with a basket and a bell	49.99	34.99	Schwinn	\N	\N	\N	Ride-Ons	\N	\N
1373	\N	\N	Balance Bike	No-pedal balance bike for learning balance and coordination	59.99	44.99	Strider	\N	\N	\N	Ride-Ons	\N	\N
1374	\N	\N	Sandbox	Blue sandbox with a lid for keeping sand clean	24.99	17.99	Little Tikes	\N	\N	\N	Outdoor	\N	\N
1375	\N	\N	Swing Set	Red and yellow swing set with two swings and a slide	99.99	69.99	Swurfer	\N	\N	\N	Outdoor	\N	\N
1376	\N	\N	Trampoline	Round trampoline with a safety net	149.99	99.99	JumpSport	\N	\N	\N	Outdoor	\N	\N
1377	\N	\N	Playhouse	Wooden playhouse with a door, windows, and a slide	199.99	149.99	KidKraft	\N	\N	\N	Outdoor	\N	\N
1378	\N	\N	Doll	18-inch doll with a variety of outfits and accessories	69.99	49.99	American Girl	\N	\N	\N	Dolls	\N	\N
1379	\N	\N	Science Kit	Science experiment kit with supplies for hands-on learning	24.99	17.99	National Geographic	\N	\N	\N	Science & Nature	\N	\N
1380	\N	\N	Microscope	Basic microscope for observing small objects	49.99	34.99	Celestron	\N	\N	\N	Science & Nature	\N	\N
1381	\N	\N	Telescope	Refractor telescope for observing stars and planets	99.99	69.99	Meade	\N	\N	\N	Science & Nature	\N	\N
1382	\N	\N	Chemistry Set	Chemistry experiment kit with safe chemicals and equipment	39.99	29.99	Elenco	\N	\N	\N	Science & Nature	\N	\N
1383	\N	\N	Art Supplies	Set of art supplies including pencils, crayons, and markers	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1384	\N	\N	Musical Instrument	Toy piano with 25 keys	29.99	21.99	Melissa & Doug	\N	\N	\N	Music	\N	\N
1385	\N	\N	Drum Set	Toy drum set with drumsticks	49.99	34.99	Little Tikes	\N	\N	\N	Music	\N	\N
1386	\N	\N	Guitar	Toy electric guitar with realistic strings and sound effects	34.99	24.99	Fisher-Price	\N	\N	\N	Music	\N	\N
1387	\N	\N	Ukulele	Toy ukulele with nylon strings	24.99	17.99	Kala	\N	\N	\N	Music	\N	\N
1388	\N	\N	Coding Robot	Educational robot that teaches basic coding concepts	99.99	79.99	Sphero	\N	\N	\N	STEM	\N	\N
1389	\N	\N	Drone	Small indoor drone with remote control	49.99	39.99	Parrot	\N	\N	\N	STEM	\N	\N
1390	\N	\N	Circuit Kit	Electronic circuit kit with components and instructions	29.99	21.99	Elenco	\N	\N	\N	STEM	\N	\N
1391	\N	\N	Building Kit	Construction kit with beams, rods, and connectors	39.99	29.99	K'NEX	\N	\N	\N	STEM	\N	\N
1392	\N	\N	Lego Set	Lego set with bricks and instructions for building various models	19.99	14.99	Lego	\N	\N	\N	STEM	\N	\N
1393	\N	\N	Board Book	Board book with simple stories and colorful illustrations	4.99	3.99	Scholastic	\N	\N	\N	Books	\N	\N
1394	\N	\N	Picture Book	Picture book with engaging stories and beautiful artwork	7.99	5.99	Disney	\N	\N	\N	Books	\N	\N
1395	\N	\N	Chapter Book	Chapter book for beginning readers	9.99	7.99	Scholastic	\N	\N	\N	Books	\N	\N
1396	\N	\N	Encyclopedia	Children's encyclopedia with information on a wide range of topics	19.99	14.99	National Geographic	\N	\N	\N	Books	\N	\N
1397	\N	\N	Activity Book	Activity book with puzzles, games, and coloring pages	4.99	3.99	Highlights	\N	\N	\N	Books	\N	\N
1398	\N	\N	Dinosaur Adventure Playset	Includes realistic dinosaur figures, interactive playmat, and sound effects	19.99	14.99	Jurassic World	\N	\N	\N	Playsets	\N	\N
1399	\N	\N	My First Princess Castle	Features a grand entrance, multiple rooms, and a working drawbridge	39.99	29.99	Disney Princess	\N	\N	\N	Playhouses	\N	\N
1400	\N	\N	Paw Patrol Pup Pad	Interactive tablet with sounds and games featuring favorite Paw Patrol characters	24.99	19.99	Paw Patrol	\N	\N	\N	Electronics	\N	\N
1401	\N	\N	Hot Wheels Mega Garage	4-level garage with multiple ramps, stunts, and storage for over 50 cars	49.99	39.99	Hot Wheels	\N	\N	\N	Playsets	\N	\N
1402	\N	\N	Barbie Dreamhouse	Iconic dollhouse with multiple rooms, furniture, and an elevator	79.99	59.99	Barbie	\N	\N	\N	Playhouses	\N	\N
1403	\N	\N	Beyblade Burst Pro Series Stadium	Official Beyblade stadium with special effects and accessories	29.99	24.99	Beyblade Burst	\N	\N	\N	Action Figures	\N	\N
1404	\N	\N	LEGO City Fire Rescue Mission	Building kit featuring a fire truck, firefighters, and a burning building	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1405	\N	\N	Nerf Ultra Strike Mechs	Double-barreled nerf gun with tactical accessories	24.99	19.99	Nerf	\N	\N	\N	Action Figures	\N	\N
1406	\N	\N	Squishmallows Rainbow Squad Plush	Super soft and cuddly plushies in rainbow colors	14.99	11.99	Squishmallows	\N	\N	\N	Stuffed Animals	\N	\N
1407	\N	\N	Play-Doh Ultimate Ice Cream Truck	Pretend ice cream truck with molds, tools, and play dough	29.99	24.99	Play-Doh	\N	\N	\N	Creative Toys	\N	\N
1408	\N	\N	CoComelon Interactive Learning JJ Doll	Talking and singing doll featuring interactive songs and phrases	24.99	19.99	CoComelon	\N	\N	\N	Dolls	\N	\N
1409	\N	\N	Hatchimals Pixies Crystal Flyers	Interactive toys that hatch, fly, and sing	19.99	14.99	Hatchimals	\N	\N	\N	Dolls	\N	\N
1410	\N	\N	Crayola Inspiration Art Case	Portable art studio with markers, crayons, paper, and stencils	29.99	24.99	Crayola	\N	\N	\N	Creative Toys	\N	\N
1411	\N	\N	Playmobil 1.2.3 Animal Care	Building kit with farm animals, barn, and accessories	19.99	14.99	Playmobil	\N	\N	\N	Building Toys	\N	\N
1412	\N	\N	Peppa Pig Talking Peppa	Interactive plush featuring Peppa's signature giggle and phrases	24.99	19.99	Peppa Pig	\N	\N	\N	Dolls	\N	\N
1413	\N	\N	Star Wars Mandalorian Helmet Electronic	Electronic helmet with authentic lights and sounds	49.99	39.99	Star Wars	\N	\N	\N	Action Figures	\N	\N
1414	\N	\N	Minecraft Steve Plush	Officially licensed Minecraft plush featuring iconic character Steve	19.99	14.99	Minecraft	\N	\N	\N	Stuffed Animals	\N	\N
1415	\N	\N	LOL Surprise OMG House of Surprises	Multi-level dollhouse with furniture, accessories, and exclusive dolls	79.99	59.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1416	\N	\N	VTech KidiZoom Creator Cam	Rugged camera with video, photo, and editing features	49.99	39.99	VTech	\N	\N	\N	Electronics	\N	\N
1417	\N	\N	Frozen II Elsa Singing Doll	Musical doll singing Let It Go and featuring iconic ice powers	29.99	24.99	Frozen II	\N	\N	\N	Dolls	\N	\N
1418	\N	\N	LEGO Star Wars Millennium Falcon	Detailed building kit featuring the iconic spaceship	149.99	129.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1419	\N	\N	Barbie Rainbow Sparkle Hair Doll	Barbie doll with long, rainbow-colored hair	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1420	\N	\N	Beyblade Burst Rise Hypersphere Vertical Drop Battle Set	Vertical battle set with stadium, launcher, and Beyblades	39.99	34.99	Beyblade Burst	\N	\N	\N	Action Figures	\N	\N
1421	\N	\N	Nerf Fortnite Heavy SR Blaster	Dart-firing blaster inspired by the popular video game	29.99	24.99	Nerf	\N	\N	\N	Action Figures	\N	\N
1422	\N	\N	Squishmallows Fuzzmallow Plush	Super soft and fluffy plushies with fuzzy textures	19.99	14.99	Squishmallows	\N	\N	\N	Stuffed Animals	\N	\N
1423	\N	\N	LEGO Harry Potter Hogwarts Express	Buildable version of the iconic train	79.99	59.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1424	\N	\N	Play-Doh Kitchen Creations Ultimate Food Truck	Realistic food truck playset with play dough and kitchen accessories	49.99	39.99	Play-Doh	\N	\N	\N	Creative Toys	\N	\N
1425	\N	\N	CoComelon Interactive Musical Learning Bus	Interactive bus with songs, lights, and educational activities	39.99	34.99	CoComelon	\N	\N	\N	Electronics	\N	\N
1426	\N	\N	Hatchimals CollEGGtibles Mermallic Mystery	Pack of surprise collectible mermaids	12.99	9.99	Hatchimals	\N	\N	\N	Dolls	\N	\N
1427	\N	\N	Crayola My First Washable Finger Paint	Finger paint perfect for young artists	9.99	7.99	Crayola	\N	\N	\N	Creative Toys	\N	\N
1428	\N	\N	Playmobil 1.2.3 Construction Site	Building kit with construction vehicles, workers, and accessories	29.99	24.99	Playmobil	\N	\N	\N	Building Toys	\N	\N
1429	\N	\N	Peppa Pig Peppa's Playtime Campervan	Toy campervan with Peppa Pig figures and accessories	39.99	34.99	Peppa Pig	\N	\N	\N	Playsets	\N	\N
1430	\N	\N	Star Wars The Child Animatronic Plush	Interactive plush featuring adorable movements and sounds	59.99	49.99	Star Wars	\N	\N	\N	Stuffed Animals	\N	\N
1431	\N	\N	Minecraft TNT Launcher Building Kit	Building kit featuring a Minecraft-themed TNT launcher	19.99	14.99	Minecraft	\N	\N	\N	Building Toys	\N	\N
1432	\N	\N	LOL Surprise Hairgoals Makeover Series	Dolls with unique hairstyles and accessories	19.99	14.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1433	\N	\N	VTech Little Apps Tablet	Learning tablet with educational apps, games, and activities	39.99	34.99	VTech	\N	\N	\N	Electronics	\N	\N
1434	\N	\N	Action Figure, Superman, 6, Poseable Figure with Cape	Action figure of Superman, the iconic superhero from DC Comics. The figure is 6 inches tall and comes with a cape. It has several points of articulation, allowing for dynamic posing and play.	15.99	11.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
1435	\N	\N	Doll, Barbie Fashionistas, Blonde Hair, Blue Eyes, Pink Dress	Barbie Fashionistas doll with blonde hair, blue eyes, and a stylish pink dress. The doll comes with a variety of accessories, including shoes, a purse, and a hairbrush.	12.99	9.99	Barbie	\N	\N	\N	Dolls	\N	\N
1436	\N	\N	Building Blocks, Mega Bloks First Builders, Big Building Bag	Mega Bloks First Builders Big Building Bag includes 80 large, colorful blocks that are perfect for little hands. The blocks are designed to be easy to stack and build with, encouraging creativity and fine motor skills.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1437	\N	\N	Board Game, Candy Land, Classic Sweet Adventure	Candy Land is a classic board game for kids ages 3 and up. Players travel along a colorful path filled with candy-themed spaces, trying to reach the Candy Castle at the end.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1438	\N	\N	Play Kitchen, KidKraft Uptown Elite Kitchen, Playset with Accessories	KidKraft Uptown Elite Kitchen is a realistic play kitchen that includes a refrigerator, oven, stove, sink, and a variety of kitchen accessories. The kitchen is made of durable wood and has a stylish design.	99.99	79.99	KidKraft	\N	\N	\N	Play Kitchens	\N	\N
1439	\N	\N	Slime Kit, Elmer's Fluffy Slime Kit, 4 Colors	Elmer's Fluffy Slime Kit includes everything you need to make 4 colors of fluffy slime. The kit comes with glitter, beads, and other decorations to customize your slime.	14.99	11.99	Elmer's	\N	\N	\N	Slime Kits	\N	\N
1440	\N	\N	Remote Control Car, Hot Wheels RC Bone Shaker	Hot Wheels RC Bone Shaker is a remote control car with a spooky design. The car features a bone-shaped body and glowing headlights. It can reach speeds of up to 20 mph and has a range of up to 100 feet.	39.99	29.99	Hot Wheels	\N	\N	\N	Remote Control Cars	\N	\N
1441	\N	\N	Stuffed Animal, Teddy Bear, Brown, 12	Teddy bear stuffed animal with brown fur and a soft, cuddly body. The bear is 12 inches tall and has embroidered eyes and nose.	19.99	14.99	Teddy Bear	\N	\N	\N	Stuffed Animals	\N	\N
1442	\N	\N	Arts and Crafts Kit, Crayola Ultimate Art Case	Crayola Ultimate Art Case includes over 140 art supplies, including crayons, markers, pencils, paint, and paper. The case is portable and easy to store, making it perfect for kids on the go.	29.99	24.99	Crayola	\N	\N	\N	Arts and Crafts Kits	\N	\N
1443	\N	\N	Educational Toy, Learning Resources Spike the Fine Motor Hedgehog	Learning Resources Spike the Fine Motor Hedgehog is an educational toy that helps develop fine motor skills. The hedgehog has a variety of textured spines that kids can push, pull, and twist to strengthen their fingers and hands.	19.99	14.99	Learning Resources	\N	\N	\N	Educational Toys	\N	\N
1444	\N	\N	Construction Toy, LEGO City Police Station	LEGO City Police Station is a construction toy that lets kids build a realistic police station. The set includes a police station building, a police car, a helicopter, and a variety of police officers and criminals.	79.99	59.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
1445	\N	\N	Dollhouse, Barbie Dreamhouse, Mansion with 8 Rooms	Barbie Dreamhouse is a mansion-sized dollhouse with 8 rooms and over 70 accessories. The dollhouse is over 3 feet tall and has a variety of features, including a working elevator, a pool, and a slide.	299.99	249.99	Barbie	\N	\N	\N	Dollhouses	\N	\N
1446	\N	\N	Ride-On Toy, Power Wheels Dune Racer	Power Wheels Dune Racer is a ride-on toy that lets kids drive over rough terrain. The dune racer has a durable design and can reach speeds of up to 5 mph. It also has a variety of features, including a working horn and headlights.	199.99	149.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
1447	\N	\N	Board Game, Monopoly Junior, Banking Game for Kids	Monopoly Junior is a banking game for kids ages 5 and up. The game is similar to the classic Monopoly game, but it is simplified for younger players.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1448	\N	\N	Science Kit, National Geographic Mega Fossil Dig Kit	National Geographic Mega Fossil Dig Kit includes everything you need to excavate 15 real fossils, including dinosaur bones, shark teeth, and seashells. The kit also comes with a magnifying glass, a brush, and a learning guide.	19.99	14.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1449	\N	\N	Slime Kit, Nick Slime Ultimate Slime Kit	Nick Slime Ultimate Slime Kit includes everything you need to make 6 different types of slime. The kit comes with glitter, beads, and other decorations to customize your slime.	24.99	19.99	Nick Slime	\N	\N	\N	Slime Kits	\N	\N
1450	\N	\N	Building Blocks, LEGO Friends Heartlake City School	LEGO Friends Heartlake City School is a construction toy that lets kids build a realistic schoolhouse. The set includes a school building, a playground, and a variety of classrooms and offices.	79.99	59.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
1451	\N	\N	Doll, LOL Surprise OMG Fierce Neonlicious	LOL Surprise OMG Fierce Neonlicious is a fashion doll with a neon-themed outfit. The doll comes with a variety of accessories, including shoes, a purse, and a hairbrush.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1452	\N	\N	Building Blocks, Mega Bloks First Builders Big Building Bag	Mega Bloks First Builders Big Building Bag includes 80 large, colorful blocks that are perfect for little hands. The blocks are designed to be easy to stack and build with, encouraging creativity and fine motor skills.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1453	\N	\N	Stuffed Animal, Squishmallows Kellytoy Squishmallow	Squishmallows Kellytoy Squishmallow is a soft and cuddly stuffed animal. The squishmallow is made of a marshmallow-like material and comes in a variety of shapes and sizes.	14.99	9.99	Kellytoy	\N	\N	\N	Stuffed Animals	\N	\N
1454	\N	\N	Board Game, Clue Junior, Mystery Game for Kids	Clue Junior is a mystery game for kids ages 5 and up. The game is similar to the classic Clue game, but it is simplified for younger players.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1455	\N	\N	Construction Toy, LEGO City Fire Station	LEGO City Fire Station is a construction toy that lets kids build a realistic fire station. The set includes a fire station building, a fire truck, a helicopter, and a variety of firefighters and civilians.	79.99	59.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
1456	\N	\N	Dollhouse, KidKraft Majestic Mansion Dollhouse	KidKraft Majestic Mansion Dollhouse is a large dollhouse with 4 levels and 10 rooms. The dollhouse is made of durable wood and has a variety of features, including a working elevator, a pool, and a slide.	249.99	199.99	KidKraft	\N	\N	\N	Dollhouses	\N	\N
1457	\N	\N	Building Blocks, Melissa & Doug Wooden Building Blocks	Melissa & Doug Wooden Building Blocks includes 100 wooden blocks in a variety of shapes and sizes. The blocks are perfect for kids to build towers, houses, and other structures.	19.99	14.99	Melissa & Doug	\N	\N	\N	Building Blocks	\N	\N
1458	\N	\N	Stuffed Animal, Aurora World Miyoni Husky	Aurora World Miyoni Husky is a soft and cuddly stuffed animal. The husky has a realistic design and is made of high-quality materials.	19.99	14.99	Aurora World	\N	\N	\N	Stuffed Animals	\N	\N
1459	\N	\N	Board Game, Candy Land, Classic Sweet Adventure	Candy Land is a classic board game for kids ages 3 and up. Players travel along a colorful path filled with candy-themed spaces, trying to reach the Candy Castle at the end.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1460	\N	\N	Science Kit, Thames & Kosmos Kids First Chemistry Lab	Thames & Kosmos Kids First Chemistry Lab includes everything you need to perform 25 basic chemistry experiments. The kit comes with a variety of materials, including chemicals, test tubes, and beakers.	19.99	14.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
1461	\N	\N	Slime Kit, Elmer's Fluffy Slime Kit, 4 Colors	Elmer's Fluffy Slime Kit includes everything you need to make 4 colors of fluffy slime. The kit comes with glitter, beads, and other decorations to customize your slime.	14.99	11.99	Elmer's	\N	\N	\N	Slime Kits	\N	\N
1462	\N	\N	Building Blocks, LEGO Star Wars The Mandalorian's N-1 Starfighter	LEGO Star Wars The Mandalorian's N-1 Starfighter is a construction toy that lets kids build a realistic starfighter from the Star Wars universe. The set includes a starfighter model, a Mandalorian minifigure, and a Grogu minifigure.	59.99	44.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
1463	\N	\N	Stuffed Animal, Ty Beanie Boos Squish-a-Boo Unicorn	Ty Beanie Boos Squish-a-Boo Unicorn is a soft and cuddly stuffed animal. The unicorn has a large, squishy body and embroidered eyes and nose.	14.99	9.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1464	\N	\N	Nerf Fortnite Basr-L Blaster	Bring home the excitement of Fortnite with the Nerf Fortnite Basr-L Blaster! This Nerf blaster is inspired by the blaster used in the popular Fortnite video game and captures the look and feel of the in-game blaster. With its bolt-action priming and detachable 6-dart clip, you can unleash a barrage of darts at your opponents.	19.99	14.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1465	\N	\N	Barbie Dreamhouse	Step into the world of Barbie with the Barbie Dreamhouse! This iconic dollhouse has 3 stories, 8 rooms, and over 70 accessories for endless imaginative play. Your child can explore the kitchen, living room, dining room, bedroom, bathroom, and even a rooftop pool.	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
1466	\N	\N	Hot Wheels Monster Trucks 5-Alarm	Get ready for monster-sized action with the Hot Wheels Monster Trucks 5-Alarm! This tough and durable monster truck is ready to crush any obstacle in its path. With its oversized tires and powerful engine, it's sure to provide hours of thrilling play.	12.99	9.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1467	\N	\N	My Little Pony Rainbow Dash	Bring the magic of My Little Pony to life with Rainbow Dash! This adorable plush pony is soft and cuddly, making it the perfect companion for any My Little Pony fan. With her colorful mane and tail, she's sure to brighten up any playroom.	19.99	14.99	My Little Pony	\N	\N	\N	Stuffed Animals	\N	\N
1468	\N	\N	LEGO Star Wars The Razor Crest	Embark on an epic adventure with the LEGO Star Wars The Razor Crest! This detailed building set features the iconic ship from the Star Wars: The Mandalorian series. With over 1,000 pieces, your child can build the Razor Crest and relive their favorite scenes from the show.	129.99	99.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1469	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Let your child's imagination soar with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck! This interactive playset comes with everything they need to create and serve their own pretend ice cream treats. With multiple molds, tools, and accessories, they can experiment with different flavors and toppings.	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1470	\N	\N	Nerf Fortnite SMG-E Blaster	Dominate the competition with the Nerf Fortnite SMG-E Blaster! This fully motorized blaster is inspired by the weapon from the popular Fortnite video game and features rapid-fire dart blasting. With its detachable 10-dart clip and slam-fire action, you'll be able to take on any opponent.	24.99	19.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1471	\N	\N	LOL Surprise OMG House of Surprises	Unleash the ultimate unboxing experience with the LOL Surprise OMG House of Surprises! This giant dollhouse stands over 3 feet tall and features 8 rooms, 4 floors, and a working elevator. With over 85 surprises to discover, your child will be entertained for hours on end.	199.99	149.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1472	\N	\N	Hot Wheels Criss Cross Crash Track Set	Get ready for high-speed action with the Hot Wheels Criss Cross Crash Track Set! This thrilling set features a dual-lane track with multiple loops, jumps, and obstacles. Your child can race their Hot Wheels cars through the track and watch them crash and collide for hours of excitement.	39.99	29.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1473	\N	\N	Barbie Fashionistas Doll	Celebrate diversity and inclusion with the Barbie Fashionistas Doll! This doll features a unique sculpt, skin tone, eye color, and hair texture. With her stylish outfit and accessories, she's sure to inspire your child's creativity and imagination.	10.99	7.99	Barbie	\N	\N	\N	Dolls	\N	\N
1474	\N	\N	LEGO Friends Heartlake City Grand Hotel	Welcome to the LEGO Friends Heartlake City Grand Hotel! This luxurious dollhouse features 5 rooms, a rooftop pool, a working elevator, and a variety of accessories. Your child can create their own hotel stories and play with their LEGO Friends mini-dolls.	99.99	79.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1475	\N	\N	Play-Doh Super Color Pack	Unlock a world of creativity with the Play-Doh Super Color Pack! This pack includes 30 cans of Play-Doh in a variety of bright and vibrant colors. Your child can mix, mold, and shape their Play-Doh creations into anything they can imagine.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1476	\N	\N	Nerf Elite 2.0 Phoenix CS-6 Blaster	Take your Nerf battles to the next level with the Nerf Elite 2.0 Phoenix CS-6 Blaster! This blaster features a rotating 6-dart drum, slam-fire action, and an adjustable stock. With its sleek design and powerful performance, it's perfect for any Nerf enthusiast.	29.99	24.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1477	\N	\N	LOL Surprise Tweens Cheer Diva	Meet the LOL Surprise Tweens Cheer Diva! This stylish doll is dressed to impress in her cheerleading outfit and comes with her own pom-poms. With her long, brushable hair and accessories, she's sure to become your child's favorite doll.	19.99	14.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1478	\N	\N	Hot Wheels Monster Trucks Mega Wrex	Prepare for monster-sized destruction with the Hot Wheels Monster Trucks Mega Wrex! This massive monster truck features oversized tires, a powerful engine, and a unique dinosaur design. With its ability to crush any obstacle in its path, it's sure to provide endless hours of thrilling play.	24.99	19.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1479	\N	\N	Barbie Dreamtopia Unicorn	Venture into the magical world of Dreamtopia with the Barbie Dreamtopia Unicorn! This enchanting unicorn features a flowing mane and tail, a glittery horn, and a colorful saddle. Your child can create their own fairy tales and embark on adventures with this majestic creature.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1480	\N	\N	LEGO Minecraft The Nether Fortress	Enter the dangerous Nether dimension with the LEGO Minecraft The Nether Fortress! This detailed building set features a fortress with a drawbridge, rotating turrets, and a variety of hostile mobs. Your child can build the fortress and recreate their favorite Minecraft adventures.	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1481	\N	\N	Play-Doh Kitchen Creations Ultimate Oven	Become a master chef with the Play-Doh Kitchen Creations Ultimate Oven! This interactive playset features a working oven, stovetop, refrigerator, and a variety of play food accessories. Your child can create their own pretend meals and experience the joy of cooking.	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1482	\N	\N	Nerf Elite 2.0 Commander RD-6 Blaster	Lead your Nerf battles to victory with the Nerf Elite 2.0 Commander RD-6 Blaster! This blaster features a rotating 6-dart drum, slam-fire action, and an adjustable stock. With its tactical rails and removable scope, you can customize it to fit your play style.	49.99	39.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1483	\N	\N	LOL Surprise OMG Cosmic Nova	Discover the cosmic wonders with the LOL Surprise OMG Cosmic Nova! This out-of-this-world doll features a futuristic outfit, glow-in-the-dark makeup, and a variety of accessories. With her unique style and personality, she's sure to become a favorite among LOL Surprise fans.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1484	\N	\N	Hot Wheels Super Ultimate Garage	Park and play with all your Hot Wheels cars in the Hot Wheels Super Ultimate Garage! This massive garage features 5 levels, 80+ parking spaces, and a variety of interactive play areas. With its spiral tracks, ramps, and stunts, your child can race and crash their cars for hours on end.	149.99	119.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1485	\N	\N	Barbie Cutie Reveal Doll	Uncover a world of cuteness with the Barbie Cutie Reveal Doll! This adorable doll comes hidden inside a plush animal and features a unique transformation. With 10 surprises to discover, your child will have hours of fun revealing the doll's outfit, makeup, and accessories.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1486	\N	\N	LEGO Star Wars The Mandalorian's Razor Crest Microfighter	Join the Mandalorian on his epic adventures with the LEGO Star Wars The Mandalorian's Razor Crest Microfighter! This miniaturized version of the iconic ship features adjustable wings, dual stud shooters, and a cockpit for the Mandalorian minifigure. Your child can recreate scenes from the show and embark on their own Star Wars missions.	9.99	7.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1487	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Cone Maker	Indulge in sweet treats with the Play-Doh Kitchen Creations Ultimate Ice Cream Cone Maker! This interactive playset lets your child create their own pretend ice cream cones with a variety of toppings. With a variety of molds and tools, they can experiment with different flavors and decorations.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1488	\N	\N	Nerf Fortnite RL Rocket Launcher	Blast into battle with the Nerf Fortnite RL Rocket Launcher! Inspired by the rocket launcher from the popular Fortnite video game, this blaster fires oversized rockets that can soar up to 100 feet. With its easy-to-load rockets and adjustable sights, you'll be ready to take on any opponent.	39.99	29.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1489	\N	\N	LOL Surprise OMG Queens Prism	Reign supreme with the LOL Surprise OMG Queens Prism! This royal doll features a stunning outfit, shimmering makeup, and a variety of accessories. With her elegant style and fierce personality, she's sure to captivate LOL Surprise fans.	29.99	24.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1490	\N	\N	Hot Wheels Color Reveal 2-Pack	Unleash the surprise with the Hot Wheels Color Reveal 2-Pack! These mystery cars come hidden in a color-changing solution. Simply dip the cars into warm water to reveal their unique designs and decorations. With a variety of different cars to collect, your child will have hours of fun discovering new surprises.	5.99	4.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1491	\N	\N	Barbie Dreamtopia Chelsea and Unicorn	Enter the magical world of Dreamtopia with Chelsea and her unicorn! This adorable doll and unicorn set features a Chelsea doll dressed in a fairy-tale outfit and a majestic unicorn with a flowing mane and tail. Your child can create their own enchanting stories and adventures.	14.99	10.99	Barbie	\N	\N	\N	Dolls	\N	\N
1492	\N	\N	LEGO Minecraft The Creeper Ambush	Outsmart the sneaky Creeper with the LEGO Minecraft The Creeper Ambush! This action-packed building set features a detailed Minecraft scene with a mine, a Creeper, and a Steve minifigure. Your child can build the scene and recreate their favorite Minecraft adventures.	19.99	14.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1493	\N	\N	Play-Doh Super Color Pack with Glitter	Add some sparkle to your Play-Doh creations with the Play-Doh Super Color Pack with Glitter! This pack includes 20 cans of Play-Doh in a variety of bright and vibrant colors, plus 4 cans of glitter Play-Doh. Your child can mix, mold, and shape their creations into anything they can imagine, all while adding a touch of sparkle.	14.99	9.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1494	\N	\N	Nerf Fortnite TS-R Pump Shotgun	Dominate the competition with the Nerf Fortnite TS-R Pump Shotgun! Inspired by the shotgun from the popular Fortnite video game, this blaster features pump-action priming and a rotating drum that holds 4 darts. With its compact size and powerful performance, you'll be ready to take on any opponent.	19.99	14.99	Nerf	\N	\N	\N	Toy Weapons	\N	\N
1495	\N	\N	LOL Surprise Boys Series 4 Doll	Meet the cool and stylish LOL Surprise Boys Series 4 Doll! This boy doll features a unique outfit, accessories, and a surprise water feature. With his trendy style and personality, he's sure to become a favorite among LOL Surprise fans.	10.99	7.99	LOL Surprise	\N	\N	\N	Dolls	\N	\N
1496	\N	\N	Hot Wheels Track Builder Unlimited Double Loop Kit	Create endless possibilities with the Hot Wheels Track Builder Unlimited Double Loop Kit! This versatile track set features multiple track pieces, connectors, and obstacles. Your child can build their own custom tracks and race their Hot Wheels cars through loops, jumps, and more.	19.99	14.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1497	\N	\N	Barbie Dreamtopia Flying Unicorn	Soar into the clouds with the Barbie Dreamtopia Flying Unicorn! This magical unicorn features a flowing mane and tail, glittery wings, and a saddle for Barbie. With its enchanting design and interactive features, your child can create their own fairy-tale adventures.	29.99	24.99	Barbie	\N	\N	\N	Dolls	\N	\N
1498	\N	\N	LEGO Minecraft The Nether Portal	Embark on an exciting adventure through the Nether with the LEGO Minecraft The Nether Portal! This detailed building set features a buildable Nether portal, a wither skeleton, and a piglin minifigure. Your child can build the portal and recreate their favorite Minecraft scenes.	19.99	14.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1499	\N	\N	Play-Doh Kitchen Creations Ultimate Spiral Fries Maker	Indulge in your favorite snack with the Play-Doh Kitchen Creations Ultimate Spiral Fries Maker! This interactive playset lets your child create their own pretend spiral fries with a variety of toppings. With a spiral cutter, fry cutter, and a variety of molds, they can experiment with different shapes and flavors.	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1500	\N	\N	Mega Bloks 80-Piece Big Building Bag	A big bag of classic Mega Bloks in a variety of colors and shapes. Perfect for building and creating all sorts of things.	9.99	7.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1501	\N	\N	LEGO Star Wars: The Child Building Kit	Build your own adorable LEGO version of The Child from the hit Disney+ series, The Mandalorian.	19.99	14.99	LEGO	\N	\N	\N	Building Blocks	\N	\N
1502	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Create and serve your own ice cream treats with this fun and interactive playset.	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1503	\N	\N	Crayola Ultimate Crayon Collection	A giant collection of 150 Crayola crayons in all the colors of the rainbow. Perfect for coloring, drawing, and creating.	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1504	\N	\N	Barbie Dreamhouse	The classic Barbie dollhouse with three stories, eight rooms, and over 70 accessories.	99.99	79.99	Barbie	\N	\N	\N	Dolls	\N	\N
1505	\N	\N	LOL Surprise! House of Surprises	A giant dollhouse with 85 surprises to unbox.	109.99	89.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1506	\N	\N	Hot Wheels Ultimate Garage	A massive garage with five levels, 36 parking spaces, and a giant loop track.	129.99	99.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1507	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	A Nerf blaster that looks like the AR-L rifle from the popular video game, Fortnite.	29.99	24.99	Nerf	\N	\N	\N	Vehicles	\N	\N
1508	\N	\N	Minecraft Dungeons Hero Edition	The ultimate Minecraft Dungeons experience with the base game and six DLC packs.	59.99	49.99	Minecraft	\N	\N	\N	Video Games	\N	\N
1509	\N	\N	Roblox Premium Membership	A premium membership for Roblox that gives you access to exclusive items, perks, and experiences.	9.99	7.99	Roblox	\N	\N	\N	Video Games	\N	\N
1510	\N	\N	Nintendo Switch Lite	A portable Nintendo Switch console that's perfect for gaming on the go.	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1511	\N	\N	PlayStation 5 Digital Edition	A next-generation video game console from Sony.	499.99	449.99	PlayStation	\N	\N	\N	Video Games	\N	\N
1512	\N	\N	Apple iPad Air (2020)	A powerful and versatile tablet from Apple.	599.99	499.99	Apple	\N	\N	\N	Electronics	\N	\N
1513	\N	\N	Samsung Galaxy Tab A7	An affordable and feature-packed tablet from Samsung.	299.99	249.99	Samsung	\N	\N	\N	Electronics	\N	\N
1514	\N	\N	Beats Solo Pro Wireless Headphones	Wireless headphones with a sleek design and powerful sound.	299.99	249.99	Beats	\N	\N	\N	Electronics	\N	\N
1515	\N	\N	Bose QuietComfort 35 II Wireless Headphones	Noise-canceling headphones that provide an immersive listening experience.	349.99	299.99	Bose	\N	\N	\N	Electronics	\N	\N
1516	\N	\N	Fujifilm Instax Mini 11 Instant Camera	A fun and easy-to-use instant camera that produces credit-card sized photos.	79.99	69.99	Fujifilm	\N	\N	\N	Electronics	\N	\N
1517	\N	\N	GoPro HERO9 Black Action Camera	A durable and versatile action camera that's perfect for capturing your adventures.	499.99	399.99	GoPro	\N	\N	\N	Electronics	\N	\N
1518	\N	\N	Nerf Fortnite TS-R Rocket Launcher	A Nerf rocket launcher that looks like the TS-R launcher from the popular video game, Fortnite.	29.99	24.99	Nerf	\N	\N	\N	Toys	\N	\N
1519	\N	\N	LEGO Minecraft The Nether Fortress	A LEGO set that lets you build and explore the Nether Fortress from the popular video game, Minecraft.	59.99	49.99	LEGO	\N	\N	\N	Toys	\N	\N
1520	\N	\N	Barbie Club Chelsea Camper	A camper van playset that's perfect for imaginative play.	39.99	29.99	Barbie	\N	\N	\N	Toys	\N	\N
1521	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm	A giant Hot Wheels monster truck that's sure to impress.	49.99	39.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1522	\N	\N	Play-Doh Super Color Pack	A pack of 36 Play-Doh containers in a variety of colors.	14.99	9.99	Play-Doh	\N	\N	\N	Toys	\N	\N
1523	\N	\N	Crayola Washable Kids' Paint	A set of washable kids' paint in a variety of colors.	9.99	7.99	Crayola	\N	\N	\N	Toys	\N	\N
1524	\N	\N	Mega Bloks First Builders Big Building Bag	A big bag of Mega Bloks designed for toddlers.	19.99	14.99	Mega Bloks	\N	\N	\N	Toys	\N	\N
1525	\N	\N	LEGO Duplo Town Farm Tractor & Animal Care	A LEGO Duplo set that lets toddlers build and explore a farm.	29.99	24.99	LEGO	\N	\N	\N	Toys	\N	\N
1526	\N	\N	Barbie Dreamtopia Mermaid Doll	A Barbie doll that transforms into a mermaid.	19.99	14.99	Barbie	\N	\N	\N	Toys	\N	\N
1527	\N	\N	LOL Surprise! Glitter Globe Doll	A LOL Surprise! doll that comes in a glitter globe.	14.99	9.99	LOL Surprise!	\N	\N	\N	Toys	\N	\N
1528	\N	\N	Hot Wheels 5-Car Pack	A pack of five Hot Wheels cars.	9.99	7.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1529	\N	\N	Nerf Elite 2.0 Echo CS-10 Blaster	A Nerf blaster that fires 10 darts in a row.	29.99	24.99	Nerf	\N	\N	\N	Toys	\N	\N
1530	\N	\N	Play-Doh Kitchen Creations Ice Cream Cone Maker	A playset that lets kids make their own Play-Doh ice cream cones.	19.99	14.99	Play-Doh	\N	\N	\N	Toys	\N	\N
1531	\N	\N	Crayola Super Tips Washable Markers	A set of 100 washable markers.	14.99	9.99	Crayola	\N	\N	\N	Toys	\N	\N
1532	\N	\N	Mega Bloks Halo UNSC Pelican Dropship	A Mega Bloks set that lets you build a UNSC Pelican dropship from the Halo video game series.	49.99	39.99	Mega Bloks	\N	\N	\N	Toys	\N	\N
1533	\N	\N	LEGO Star Wars: The Razor Crest	A LEGO set that lets you build The Razor Crest ship from the Disney+ series, The Mandalorian.	129.99	99.99	LEGO	\N	\N	\N	Toys	\N	\N
1534	\N	\N	Remote Control Car	Blue and red remote control car with lights and sounds, top speed 10 mph, for ages 8+	12.99	9.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1535	\N	\N	Barbie Dreamhouse	Pink and white dollhouse with 3 stories, 6 rooms, and a working elevator, for ages 3+	39.99	29.99	Barbie	\N	\N	\N	Dolls	\N	\N
1536	\N	\N	Nerf Fortnite Blaster	Blue and orange toy blaster that shoots foam darts, for ages 8+	19.99	14.99	Nerf	\N	\N	\N	Toys	\N	\N
1537	\N	\N	Pokemon Trading Card Game	Box of 36 Pokemon trading cards, for ages 6+	14.99	10.99	Pokemon	\N	\N	\N	Games	\N	\N
1538	\N	\N	Lego Star Wars Building Set	1,000-piece building set featuring the Millennium Falcon, for ages 9+	49.99	39.99	Lego	\N	\N	\N	Toys	\N	\N
1539	\N	\N	Hatchimals Collectible Egg	Pink and purple egg that hatches into a surprise Hatchimal, for ages 5+	9.99	7.99	Hatchimals	\N	\N	\N	Toys	\N	\N
1540	\N	\N	Shopkins Shoppies Doll	Pink and white doll with glittery outfit, for ages 5+	14.99	10.99	Shopkins	\N	\N	\N	Dolls	\N	\N
1541	\N	\N	Roblox Gift Card	$25 gift card for the online game Roblox, for ages 8+	25.00	25.00	Roblox	\N	\N	\N	Games	\N	\N
1542	\N	\N	Fortnite Battle Royale Action Figure	7-inch action figure of the popular video game character, for ages 8+	14.99	10.99	Fortnite	\N	\N	\N	Toys	\N	\N
1543	\N	\N	Crayola Ultimate Crayon Collection	150-count box of crayons in various colors, for ages 3+	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1544	\N	\N	Play-Doh Modeling Compound	12-pack of Play-Doh modeling compound in various colors, for ages 2+	14.99	10.99	Play-Doh	\N	\N	\N	Toys	\N	\N
1545	\N	\N	Minecraft Building Blocks	Set of 200 building blocks inspired by the video game Minecraft, for ages 6+	19.99	14.99	Minecraft	\N	\N	\N	Toys	\N	\N
1546	\N	\N	LOL Surprise! Doll	Pink and gold doll with surprise accessories, for ages 6+	14.99	10.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1547	\N	\N	Hot Wheels Track Set	Blue and orange track set with loops and jumps, for ages 5+	24.99	19.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1548	\N	\N	Star Wars Lightsaber	Red and blue lightsaber toy with sound effects, for ages 6+	19.99	14.99	Star Wars	\N	\N	\N	Toys	\N	\N
1549	\N	\N	Unicorn Slime Kit	Kit that includes slime, glitter, and instructions for making unicorn slime, for ages 8+	14.99	10.99	Unicorn Slime Kit	\N	\N	\N	Toys	\N	\N
1550	\N	\N	PAW Patrol Lookout Tower Playset	Blue and yellow playset featuring the PAW Patrol characters, for ages 3+	39.99	29.99	PAW Patrol	\N	\N	\N	Toys	\N	\N
1551	\N	\N	Frozen Elsa Doll	Blue and white doll of the popular Disney character, for ages 3+	19.99	14.99	Frozen	\N	\N	\N	Dolls	\N	\N
1552	\N	\N	Marvel Avengers Iron Man Action Figure	Red and gold action figure of the popular Marvel character, for ages 5+	14.99	10.99	Marvel Avengers	\N	\N	\N	Toys	\N	\N
1553	\N	\N	Jurassic World Dinosaur Figure	Green and brown dinosaur figure of the popular movie character, for ages 3+	19.99	14.99	Jurassic World	\N	\N	\N	Toys	\N	\N
1554	\N	\N	Nerf Fortnite Pump Shotgun	Orange and blue toy shotgun that shoots foam darts, for ages 8+	19.99	14.99	Nerf	\N	\N	\N	Toys	\N	\N
1555	\N	\N	Barbie Fashion Doll	Pink and white doll with glittery outfit, for ages 3+	14.99	10.99	Barbie	\N	\N	\N	Dolls	\N	\N
1556	\N	\N	Hot Wheels Super 6 Lane Race Track	Blue and orange race track with 6 lanes and a loop, for ages 5+	39.99	29.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1557	\N	\N	Paw Patrol Ultimate Fire Truck	Red and white fire truck toy with lights and sounds, for ages 3+	39.99	29.99	Paw Patrol	\N	\N	\N	Toys	\N	\N
1558	\N	\N	Nerf Elite 2.0 Echo CS-10 Blaster	Blue and white toy blaster that shoots foam darts, for ages 8+	24.99	19.99	Nerf	\N	\N	\N	Toys	\N	\N
1559	\N	\N	Barbie Dreamtopia Magic Unicorn	Pink and white unicorn toy with lights and sounds, for ages 3+	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1560	\N	\N	Hot Wheels Monster Trucks Live Mega Wrex	Blue and orange monster truck toy with lights and sounds, for ages 4+	24.99	19.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
1561	\N	\N	LOL Surprise! OMG House of Surprises	Pink and white dollhouse with 4 stories, 6 rooms, and a working elevator, for ages 6+	79.99	59.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1562	\N	\N	Hatchimals Pixies Crystal Flyers	Pink and purple toy pixie that flies, for ages 5+	14.99	10.99	Hatchimals	\N	\N	\N	Toys	\N	\N
1563	\N	\N	Minecraft Dungeons Hero Edition	Video game for Nintendo Switch, Xbox One, and PlayStation 4, for ages 10+	39.99	29.99	Minecraft	\N	\N	\N	Games	\N	\N
1564	\N	\N	Roblox Adopt Me! Pet Wear Accessory Pack	Set of pet accessories for the online game Roblox Adopt Me!, for ages 8+	14.99	10.99	Roblox	\N	\N	\N	Games	\N	\N
1565	\N	\N	Crayola Washable Sidewalk Chalk	Box of 12 washable sidewalk chalk sticks in various colors, for ages 3+	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1566	\N	\N	PAW Patrol Mighty Pups Super Paws Skye	Blue and pink toy jet with lights and sounds, for ages 3+	24.99	19.99	Paw Patrol	\N	\N	\N	Toys	\N	\N
1567	\N	\N	Fortnite Battle Royale Legendary Series Action Figure	Gold and black action figure of the popular video game character, for ages 8+	19.99	14.99	Fortnite	\N	\N	\N	Toys	\N	\N
1568	\N	\N	Lego Star Wars Millennium Falcon	The Lego Star Wars Millennium Falcon is a great gift for any Star Wars fan. It has over 1,000 pieces and is very detailed. It comes with 4 minifigures: Han Solo, Chewbacca, Princess Leia, and Luke Skywalker.	149.99	129.99	Lego	\N	\N	\N	Building Toys	\N	\N
1569	\N	\N	Barbie Dreamhouse	The Barbie Dreamhouse is a classic toy that has been around for generations. It is a large dollhouse with 3 floors and 8 rooms. It comes with over 70 pieces of furniture and accessories.	199.99	169.99	Barbie	\N	\N	\N	Dolls	\N	\N
1570	\N	\N	Hot Wheels Ultimate Garage	The Hot Wheels Ultimate Garage is a huge playset that can hold over 100 cars. It has 5 levels and a spiral track. It comes with 10 Hot Wheels cars.	99.99	89.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1571	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	The Nerf Fortnite AR-L Elite Dart Blaster is a toy gun that shoots foam darts. It is based on the Fortnite video game. It comes with 20 darts.	29.99	24.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
1572	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	The Play-Doh Kitchen Creations Ultimate Ice Cream Truck is a playset that lets kids create their own ice cream treats. It comes with a variety of Play-Doh colors and tools.	29.99	24.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
1573	\N	\N	Action Figure: Spider-Man	Bendable and poseable Spider-Man action figure.	14.99	11.99	Marvel	\N	\N	\N	Action Figures & Playsets	\N	\N
1574	\N	\N	Minecraft Dungeons Battle Tower	The Minecraft Dungeons Battle Tower is a building set that lets kids build their own Minecraft tower. It comes with over 400 pieces and 4 minifigures.	29.99	24.99	Minecraft	\N	\N	\N	Building Toys	\N	\N
1575	\N	\N	LOL Surprise! OMG House of Surprises	The LOL Surprise! OMG House of Surprises is a large playset that comes with 85 surprises. It has 4 floors and 10 rooms. It comes with 4 LOL Surprise! dolls.	199.99	169.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1576	\N	\N	Ryan's World Mega Mystery Box	The Ryan's World Mega Mystery Box is a large box that comes with over 50 surprises. It includes toys, games, and other items from the Ryan's World YouTube channel.	49.99	39.99	Ryan's World	\N	\N	\N	Toys	\N	\N
1577	\N	\N	Paw Patrol Lookout Tower	The Paw Patrol Lookout Tower is a playset that lets kids recreate their favorite scenes from the Paw Patrol TV show. It comes with 6 figures and a vehicle.	49.99	39.99	Paw Patrol	\N	\N	\N	Building Toys	\N	\N
1578	\N	\N	Hatchimals CollEGGtibles 12-Pack Egg Carton	The Hatchimals CollEGGtibles 12-Pack Egg Carton comes with 12 Hatchimals eggs. Each egg contains a surprise creature.	19.99	14.99	Hatchimals	\N	\N	\N	Toys	\N	\N
1579	\N	\N	Beyblade Burst Turbo Slingshock Beystadium	The Beyblade Burst Turbo Slingshock Beystadium is a toy arena that lets kids battle their Beyblades. It comes with 2 Beyblades.	19.99	14.99	Beyblade	\N	\N	\N	Toy Tops	\N	\N
1580	\N	\N	Funko Pop! Star Wars: The Mandalorian - The Child	The Funko Pop! Star Wars: The Mandalorian - The Child is a collectible figure of the popular character from the Mandalorian TV show.	14.99	11.99	Funko	\N	\N	\N	Collectibles	\N	\N
1581	\N	\N	Crayola Ultimate Crayon Collection	The Crayola Ultimate Crayon Collection comes with 150 crayons in a variety of colors.	19.99	14.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
1582	\N	\N	Melissa & Doug Wooden Activity Table	The Melissa & Doug Wooden Activity Table is a large activity table that comes with a variety of activities for kids to enjoy.	79.99	69.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
1583	\N	\N	VTech KidiZoom Creator Cam	The VTech KidiZoom Creator Cam is a digital camera that is perfect for kids. It comes with a variety of features, including a selfie stick and a green screen.	49.99	39.99	VTech	\N	\N	\N	Electronics	\N	\N
1584	\N	\N	LeapFrog LeapPad Platinum	The LeapFrog LeapPad Platinum is a tablet that is perfect for kids. It comes with a variety of educational games and apps.	149.99	129.99	LeapFrog	\N	\N	\N	Electronics	\N	\N
1585	\N	\N	Razor E100 Electric Scooter	The Razor E100 Electric Scooter is a great way for kids to get around. It has a top speed of 10 mph and a range of up to 10 miles.	199.99	169.99	Razor	\N	\N	\N	Toys	\N	\N
1586	\N	\N	Schwinn Elm Kids Bike	The Schwinn Elm Kids Bike is a great bike for kids who are learning to ride. It has a sturdy frame and a variety of safety features.	149.99	129.99	Schwinn	\N	\N	\N	Toys	\N	\N
1587	\N	\N	Nerf Fortnite BASR-L Elite Dart Blaster	The Nerf Fortnite BASR-L Elite Dart Blaster is a toy gun that shoots foam darts. It is based on the Fortnite video game. It comes with 6 darts.	19.99	14.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
1588	\N	\N	Play-Doh Kitchen Creations Pizza Party Playset	The Play-Doh Kitchen Creations Pizza Party Playset is a playset that lets kids create their own pizza treats. It comes with a variety of Play-Doh colors and tools.	19.99	14.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
1589	\N	\N	Minecraft Dungeons Redstone Battle	The Minecraft Dungeons Redstone Battle is a building set that lets kids build their own Minecraft battle scene. It comes with over 300 pieces and 4 minifigures.	24.99	19.99	Minecraft	\N	\N	\N	Building Toys	\N	\N
1590	\N	\N	LOL Surprise! Bigger Surprise	The LOL Surprise! Bigger Surprise comes with over 60 surprises. It includes dolls, pets, and other items from the LOL Surprise! line.	69.99	59.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1591	\N	\N	Ryan's World Giant Mystery Egg	The Ryan's World Giant Mystery Egg comes with over 20 surprises. It includes toys, games, and other items from the Ryan's World YouTube channel.	29.99	24.99	Ryan's World	\N	\N	\N	Toys	\N	\N
1592	\N	\N	Paw Patrol Mighty Lookout Tower	The Paw Patrol Mighty Lookout Tower is a playset that lets kids recreate their favorite scenes from the Paw Patrol TV show. It comes with 6 figures and a vehicle.	69.99	59.99	Paw Patrol	\N	\N	\N	Building Toys	\N	\N
1593	\N	\N	Hatchimals CollEGGtibles Shimmering Seas 4-Pack	The Hatchimals CollEGGtibles Shimmering Seas 4-Pack comes with 4 Hatchimals eggs. Each egg contains a surprise creature that changes color when it is submerged in water.	9.99	7.99	Hatchimals	\N	\N	\N	Toys	\N	\N
1594	\N	\N	Beyblade Burst Turbo Slingshock Starter Pack	The Beyblade Burst Turbo Slingshock Starter Pack comes with 1 Beyblade and a launcher. It is a great way to get started with Beyblade.	14.99	11.99	Beyblade	\N	\N	\N	Toy Tops	\N	\N
1595	\N	\N	Funko Pop! Harry Potter: Hedwig	The Funko Pop! Harry Potter: Hedwig is a collectible figure of the popular owl from the Harry Potter series.	14.99	11.99	Funko	\N	\N	\N	Collectibles	\N	\N
1596	\N	\N	Hot Wheels Ultimate Garage Tower	Massive 5-foot tower with 8 levels, 70+ parking spaces, & a 2-car elevator	64.99	49.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1597	\N	\N	LEGO Star Wars The Razor Crest	Detailed model of the Mandalorian's ship with minifigures of Din Djarin	139.99	99.99	LEGO	\N	\N	\N	Building	\N	\N
1598	\N	\N	Barbie Dreamhouse	3-story dollhouse with 10 rooms, an elevator & a pool	199.99	159.99	Barbie	\N	\N	\N	Dollhouse	\N	\N
1599	\N	\N	Nerf Fortnite BASR-L Blaster	Sniper rifle replica with a removable scope & 6 Nerf Fortnite darts	29.99	19.99	Nerf	\N	\N	\N	Outdoor	\N	\N
1600	\N	\N	Nintendo Switch Lite	Compact version of the Nintendo Switch with a built-in screen	199.99	179.99	Nintendo	\N	\N	\N	Gaming	\N	\N
1601	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Playset with a truck, molds, & tools for kids to create their own ice cream treats	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
1602	\N	\N	LOL Surprise! OMG House of Surprises	4-story dollhouse with 10 rooms, 85+ surprises & an exclusive LOL Surprise! doll	169.99	129.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1603	\N	\N	Minecraft Dungeons Battle Tower	Building set with 228 pieces, a tower, a catapult & 3 minifigures	29.99	24.99	LEGO	\N	\N	\N	Building	\N	\N
1604	\N	\N	Paw Patrol Mighty Lookout Tower	3-foot tall tower with a working elevator, lights & sounds	79.99	59.99	Paw Patrol	\N	\N	\N	TV & Movies	\N	\N
1605	\N	\N	Hatchimals Pixies Crystal Flyers	Interactive pixie toys that fly & light up	19.99	14.99	Hatchimals	\N	\N	\N	Dolls	\N	\N
1606	\N	\N	Crayola Mess-Free Washable Paint	16-pack of washable paint bottles with a built-in dispenser	14.99	11.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1607	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Magnetic doll with multiple outfits & accessories	19.99	16.99	Melissa & Doug	\N	\N	\N	Educational	\N	\N
1608	\N	\N	ThinkFun Gravity Maze Marble Run	Puzzle game with 60 challenges & a 3D maze	29.99	24.99	ThinkFun	\N	\N	\N	Educational	\N	\N
1609	\N	\N	National Geographic Kids Science Encyclopedia	Informative encyclopedia with over 1,000 pages of science facts & photos	24.99	19.99	National Geographic Kids	\N	\N	\N	Books	\N	\N
1610	\N	\N	Klutz LEGO Chain Reactions Science & Building Kit	Kit with 30+ LEGO bricks, chain reactions & experiments	29.99	24.99	Klutz	\N	\N	\N	Educational	\N	\N
1611	\N	\N	Ravensburger Gravitrax Starter Set	Marble run system with curves, tracks & magnetic launchers	49.99	39.99	Ravensburger	\N	\N	\N	Building	\N	\N
1612	\N	\N	Barbie Made to Move Doll	Doll with 22 points of articulation & flexible joints	19.99	16.99	Barbie	\N	\N	\N	Dolls	\N	\N
1613	\N	\N	LEGO Friends Friendship House	3-story house with 4 mini-dolls, a kitchen & a rooftop terrace	79.99	59.99	LEGO	\N	\N	\N	Building	\N	\N
1614	\N	\N	Hot Wheels Criss Cross Crash Track Playset	Track set with 2 crash zones, 5 cars & a launcher	29.99	24.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1615	\N	\N	Nerf Fortnite RL Blaster	Rocket launcher replica with a removable magazine & 2 Nerf Fortnite rockets	39.99	29.99	Nerf	\N	\N	\N	Outdoor	\N	\N
1616	\N	\N	Pokémon Trading Card Game: Sword & Shield Brilliant Stars	Box with 10 booster packs & a promo card	14.99	11.99	Pokémon	\N	\N	\N	Games	\N	\N
1617	\N	\N	Nintendo Switch Mario Kart 8 Deluxe	Racing game with 48 tracks & a variety of characters	59.99	49.99	Nintendo	\N	\N	\N	Gaming	\N	\N
1618	\N	\N	L.O.L. Surprise! O.M.G. Lights Glitter Globe	Glitter globe with an exclusive L.O.L. Surprise! doll	29.99	24.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1619	\N	\N	Just Dance 2023	Dancing game with over 40 tracks & a free month of Just Dance Unlimited	49.99	39.99	Ubisoft	\N	\N	\N	Gaming	\N	\N
1620	\N	\N	Nerf Elite 2.0 Warden DB-8 Blaster	Double-barrel blaster with 8 darts & a removable scope	29.99	24.99	Nerf	\N	\N	\N	Outdoor	\N	\N
1621	\N	\N	Hot Wheels Track Builder Unlimited Corkscrew Twist Kit	Expansion kit with a corkscrew track, banked curves & a jump	24.99	19.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1622	\N	\N	LEGO Minecraft The Nether Portal	Building set with over 400 pieces, a portal & 2 minifigures	19.99	16.99	LEGO	\N	\N	\N	Building	\N	\N
1623	\N	\N	Barbie Cutie Reveal Ken Doll	Ken doll with a plush animal costume that transforms into a jacket	19.99	16.99	Barbie	\N	\N	\N	Dolls	\N	\N
1624	\N	\N	Hot Wheels Monster Trucks Live Megalodon Storm	Remote-controlled monster truck with lights & sounds	49.99	39.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1625	\N	\N	Pokémon TCG: Sword & Shield—Astral Radiance Build & Battle Stadium	Box with 4 booster packs, 2 theme decks & a playmat	49.99	39.99	Pokémon	\N	\N	\N	Games	\N	\N
1626	\N	\N	Nintendo Switch Lite Gray	Compact version of the Nintendo Switch in gray	199.99	179.99	Nintendo	\N	\N	\N	Gaming	\N	\N
1627	\N	\N	Nerf Fortnite SMASH-3 Blaster	Hammer-action blaster with a removable barrel & 3 Nerf Fortnite darts	29.99	19.99	Nerf	\N	\N	\N	Outdoor	\N	\N
1628	\N	\N	LEGO Harry Potter Hogwarts Express	Detailed model of the Hogwarts Express train with a minifigure of Harry Potter	79.99	59.99	LEGO	\N	\N	\N	Building	\N	\N
1629	\N	\N	Hot Wheels City Ultimate Garage	Massive 5-foot garage with 3 levels, a spiral ramp & a car elevator	149.99	99.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
1630	\N	\N	Nintendo Switch OLED	Upgraded version of the Nintendo Switch with a larger OLED screen	349.99	299.99	Nintendo	\N	\N	\N	Gaming	\N	\N
1631	\N	\N	Action Figure, 12 Captain America, Detailed Design, Movable Joints, Shield and Sword Accessories	Highly detailed 12-inch Captain America action figure with authentic movie design, multiple points of articulation, and included shield and sword accessories for dynamic action play.	24.99	19.99	Hasbro	\N	\N	\N	Action Figures	\N	\N
1632	\N	\N	Doll, 18 My Life As Veterinarian, Realistic Features, Medical Accessories	18-inch My Life As Veterinarian doll with realistic features, soft body, and a variety of medical accessories, including a stethoscope, syringes, and a pet carrier.	39.99	29.99	Melissa & Doug	\N	\N	\N	Dolls	\N	\N
1633	\N	\N	Building Blocks, 500-Piece Mega Bloks First Builders Classic, Bright Colors, Large Size	500-piece set of Mega Bloks First Builders classic building blocks in bright colors and large size, designed for toddlers and preschoolers to explore creativity and develop fine motor skills.	19.99	14.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1634	\N	\N	Board Game, Monopoly Junior, Classic Family Fun, Simplified Rules	Monopoly Junior board game, a simplified version of the classic family game, designed for younger players with shorter playing time and easy-to-understand rules.	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1635	\N	\N	Stuffed Animal, 12 Cuddlekins Teddy Bear, Soft and Huggable	12-inch Cuddlekins teddy bear made from soft and huggable plush fabric, with embroidered eyes, nose, and mouth, and a bow tie.	14.99	9.99	Gund	\N	\N	\N	Stuffed Animals	\N	\N
1636	\N	\N	Science Kit, National Geographic Mega Fossil Dig, 15 Real Fossils	National Geographic Mega Fossil Dig science kit containing 15 real fossils, including dinosaur bones, shark teeth, and ammonites, along with excavation tools and a learning guide.	29.99	24.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1637	\N	\N	Remote Control Car, 1:18 Scale Lamborghini Huracan, High Speed, LED Lights	1:18 scale remote control Lamborghini Huracan car with realistic details, high speed, and working LED lights.	49.99	39.99	Maisto	\N	\N	\N	Remote Control Cars	\N	\N
1638	\N	\N	Play Tent, Pop-Up Castle with Tunnel, Indoor and Outdoor Play	Pop-up play tent in the shape of a castle with an attached tunnel, providing a fun and imaginative play space for kids indoors or outdoors.	34.99	24.99	Melissa & Doug	\N	\N	\N	Play Tents	\N	\N
1639	\N	\N	Art Supplies, Crayola 140-Count Crayon Set, Vibrant Colors, Washable	140-count Crayola crayon set featuring a wide range of vibrant colors, designed for aspiring artists of all ages.	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1640	\N	\N	Musical Instrument, Yamaha PSS-F30 Digital Keyboard, 37 Keys, Built-In Speakers	Yamaha PSS-F30 digital keyboard with 37 keys, built-in speakers, and a variety of sound effects and rhythms.	79.99	59.99	Yamaha	\N	\N	\N	Musical Instruments	\N	\N
1641	\N	\N	Sports Equipment, Nerf Fortnite BASR-L Blaster, Motorized, Dart-Firing	Nerf Fortnite BASR-L blaster, a motorized dart-firing blaster inspired by the popular video game, featuring a removable scope and bipod.	49.99	34.99	Hasbro	\N	\N	\N	Sports Equipment	\N	\N
1642	\N	\N	Video Game, Nintendo Switch Lite, Blue, Handheld Console	Nintendo Switch Lite handheld console in blue, designed for portable gaming with a sleek and compact design.	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1643	\N	\N	Book, Harry Potter and the Philosopher's Stone, J.K. Rowling, Fantasy Adventure	Harry Potter and the Philosopher's Stone book by J.K. Rowling, the first installment in the beloved fantasy adventure series.	14.99	10.99	Scholastic	\N	\N	\N	Books	\N	\N
1644	\N	\N	Movie, Frozen II, Blu-ray + DVD, Animated Adventure	Frozen II Blu-ray + DVD combo pack featuring the sequel to the popular animated adventure film.	29.99	19.99	Disney	\N	\N	\N	Movies	\N	\N
1645	\N	\N	Puzzle, Ravensburger 1000-Piece Jigsaw Puzzle, Tropical Rainforest	Ravensburger 1000-piece jigsaw puzzle depicting a vibrant and lush tropical rainforest scene.	19.99	14.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1646	\N	\N	Bike, Schwinn Elm 24, Blue, Single Speed	Schwinn Elm 24 bike in blue, a single-speed bicycle designed for kids ages 8-12 with a sturdy steel frame and adjustable seat.	199.99	149.99	Schwinn	\N	\N	\N	Bikes	\N	\N
1647	\N	\N	Scooter, Razor A5 Lux Kick Scooter, Black and Silver, Adjustable Height	Razor A5 Lux kick scooter in black and silver, featuring an adjustable height handlebar, large wheels, and a folding mechanism for easy storage.	99.99	79.99	Razor	\N	\N	\N	Scooters	\N	\N
1648	\N	\N	Rollerblades, Rollerblade Microblade 3WD Adjustable Inline Skates, Black and Pink	Rollerblade Microblade 3WD adjustable inline skates in black and pink, designed for beginners and recreational skaters.	99.99	79.99	Rollerblade	\N	\N	\N	Rollerblades	\N	\N
1649	\N	\N	Skateboard, SK8 Mafia Skull Skater Complete Skateboard, 7.75	SK8 Mafia Skull Skater complete skateboard with a 7.75 deck, durable trucks, and high-quality bearings, perfect for beginners and experienced skaters.	79.99	59.99	SK8 Mafia	\N	\N	\N	Skateboards	\N	\N
1650	\N	\N	Trampoline, Skywalker 8-Foot Round Trampoline with Enclosure Net	Skywalker 8-foot round trampoline with enclosure net, providing a safe and fun way to bounce and play.	299.99	249.99	Skywalker	\N	\N	\N	Trampolines	\N	\N
1651	\N	\N	Pool, Intex 8-Foot Easy Set Inflatable Pool, Above Ground	Intex 8-foot Easy Set inflatable pool, an affordable and easy-to-set-up above-ground pool for summer fun.	99.99	79.99	Intex	\N	\N	\N	Pools	\N	\N
1652	\N	\N	Water Gun, Super Soaker Fortnite HC-E Mega Water Blaster, High Capacity	Super Soaker Fortnite HC-E Mega water blaster, inspired by the popular video game, featuring a high-capacity tank and adjustable nozzle.	29.99	19.99	Hasbro	\N	\N	\N	Water Toys	\N	\N
1653	\N	\N	Craft Kit, LEGO Minecraft The Crafting Box 3.0, Building Blocks and Accessories	LEGO Minecraft The Crafting Box 3.0 building blocks and accessories set, featuring iconic characters and items from the popular video game.	29.99	24.99	LEGO	\N	\N	\N	Craft Kits	\N	\N
1654	\N	\N	Play-Doh, Play-Doh 36-Pack of Colors, Modeling Compound	36-pack of Play-Doh modeling compound in various colors, providing endless opportunities for creative play and imagination.	19.99	14.99	Hasbro	\N	\N	\N	Play-Doh	\N	\N
1655	\N	\N	Nerf Gun, Nerf Fortnite SMG-E Blaster, Motorized, Burst Fire	Nerf Fortnite SMG-E blaster, a motorized burst-fire blaster inspired by the popular video game, featuring a detachable drum magazine.	29.99	19.99	Hasbro	\N	\N	\N	Nerf Guns	\N	\N
1656	\N	\N	Slime Kit, Elmer's Magical Liquid Slime Kit, 4 Colors	Elmer's Magical Liquid Slime Kit containing 4 colors of pre-made slime, glitter, and mixing tools for endless slimy fun.	19.99	14.99	Elmer's	\N	\N	\N	Slime Kits	\N	\N
1657	\N	\N	Kinetic Sand, National Geographic Play Sand, 2-Pound Container	National Geographic Play Sand, a moldable and squeezable kinetic sand that provides a unique sensory play experience.	14.99	9.99	National Geographic	\N	\N	\N	Kinetic Sand	\N	\N
1658	\N	\N	Board Game, Candy Land, Classic Family Fun, Sweet Adventure	Candy Land board game, a classic family game featuring a sweet and colorful adventure through a candy-themed world.	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1659	\N	\N	Card Game, Pokémon Trading Card Game: Sword & Shield Base Set Booster Pack	Pokémon Trading Card Game: Sword & Shield Base Set booster pack containing 10 randomized cards featuring popular Pokémon characters and abilities.	4.99	3.99	The Pokémon Company	\N	\N	\N	Card Games	\N	\N
1660	\N	\N	Building Blocks, LEGO Classic Medium Creative Brick Box, 484 Pieces	LEGO Classic Medium Creative Brick Box containing 484 pieces in various colors and shapes, inspiring creativity and building adventures.	49.99	39.99	LEGO	\N	\N	\N	Building Blocks	\N	\N
1661	\N	\N	Stuffed Animal, Ty Beanie Baby, Princess Diana Bear, Collectible	Ty Beanie Baby Princess Diana bear, a collectible and commemorative plush animal honoring the late Princess of Wales.	19.99	14.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1662	\N	\N	Science Kit, Thames & Kosmos Kids First Chemistry Kit, 25 Experiments	Thames & Kosmos Kids First Chemistry Kit containing 25 fun and educational chemistry experiments, designed for young scientists.	29.99	24.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
1663	\N	\N	Musical Instrument, Ukulele, Kala Learn-to-Play Ukulele Starter Kit	Kala Learn-to-Play Ukulele Starter Kit, including a ukulele, tuner, instructional DVD, and a carry bag.	79.99	59.99	Kala	\N	\N	\N	Musical Instruments	\N	\N
1664	\N	\N	Sports Equipment, Wilson NFL Team Football, Official Size	Wilson NFL Team football in the colors and logo of your favorite NFL team, providing authentic gameplay experience.	29.99	19.99	Wilson	\N	\N	\N	Sports Equipment	\N	\N
1665	\N	\N	Video Game, Minecraft Dungeons: Ultimate Edition, Nintendo Switch	Minecraft Dungeons: Ultimate Edition for Nintendo Switch, including the base game and all downloadable content.	29.99	19.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
1666	\N	\N	Book, Diary of a Wimpy Kid: Big Shot, Jeff Kinney, Middle School Misadventures	Diary of a Wimpy Kid: Big Shot book by Jeff Kinney, the latest installment in the popular middle school misadventures series.	14.99	10.99	Amulet Books	\N	\N	\N	Books	\N	\N
1667	\N	\N	Movie, Star Wars: The Rise of Skywalker, Blu-ray + DVD, Epic Conclusion	Star Wars: The Rise of Skywalker Blu-ray + DVD combo pack featuring the epic conclusion to the Skywalker saga.	29.99	19.99	Disney	\N	\N	\N	Movies	\N	\N
1668	\N	\N	Stunt Scooter	Razor Stunt Scooter with 12-Inch Wheels, Rear Caliper Brake, and Pro-Style BMX Handlebars	149.99	129.99	Razor	\N	\N	\N	Scooters	\N	\N
1669	\N	\N	Gaming Headset	Turtle Beach Recon 70 Gaming Headset for Xbox Series X, S, Xbox One, PS5, PS4, Nintendo Switch, Mobile, and PC	39.99	29.99	Turtle Beach	\N	\N	\N	Gaming Accessories	\N	\N
1670	\N	\N	Nerf Fortnite SMG-E Blaster	Nerf Fortnite SMG-E Blaster with 6 Official Nerf Fortnite Darts	19.99	14.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
1671	\N	\N	Minecraft Dungeons Hero Edition	Minecraft Dungeons Hero Edition for Xbox Series X, S, Xbox One, PS5, PS4, Nintendo Switch, and PC	29.99	19.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
1672	\N	\N	LEGO Star Wars: The Skywalker Saga	LEGO Star Wars: The Skywalker Saga for Xbox Series X, S, Xbox One, PS5, PS4, Nintendo Switch, and PC	59.99	49.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1673	\N	\N	Barbie Dreamhouse	Barbie Dreamhouse with 3 Stories, 8 Rooms, and a Working Elevator	199.99	149.99	Barbie	\N	\N	\N	Dolls	\N	\N
1674	\N	\N	Hot Wheels Ultimate Garage	Hot Wheels Ultimate Garage with 6 Levels, 360-Degree Spiral Track, and Slam Launcher	149.99	119.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1675	\N	\N	Nintendo Switch Lite	Nintendo Switch Lite in Turquoise	199.99	179.99	Nintendo	\N	\N	\N	Video Game Consoles	\N	\N
1676	\N	\N	Beyblade Burst QuadDrive Cosmic Vector Beystadium	Beyblade Burst QuadDrive Cosmic Vector Beystadium with 4 Launchers	29.99	24.99	Hasbro	\N	\N	\N	Beyblades	\N	\N
1677	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset with 28 Accessories	29.99	24.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
1678	\N	\N	Nerf Fortnite AR-L Elite Dart Blaster	Nerf Fortnite AR-L Elite Dart Blaster with 20 Official Nerf Fortnite Elite Darts	24.99	19.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
1679	\N	\N	LOL Surprise! OMG House of Surprises	LOL Surprise! OMG House of Surprises with 85+ Surprises	109.99	89.99	LOL Surprise!	\N	\N	\N	Dolls	\N	\N
1680	\N	\N	Minecraft Dungeons Season Pass	Minecraft Dungeons Season Pass for Xbox Series X, S, Xbox One, PS5, PS4, Nintendo Switch, and PC	19.99	14.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
1681	\N	\N	Hot Wheels id Smart Track Kit	Hot Wheels id Smart Track Kit with 1 Vehicle and 1 Track Piece	39.99	29.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1682	\N	\N	Nintendo Switch Online Family Membership	Nintendo Switch Online Family Membership for 12 Months	34.99	29.99	Nintendo	\N	\N	\N	Video Game Subscriptions	\N	\N
1683	\N	\N	Crayola Ultimate Crayon Collection	Crayola Ultimate Crayon Collection with 150 Crayons	19.99	14.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
1684	\N	\N	LEGO Minecraft The Nether Bastion	LEGO Minecraft The Nether Bastion with 222 Pieces	29.99	24.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1685	\N	\N	Harry Potter Hogwarts Castle	LEGO Harry Potter Hogwarts Castle with 6020 Pieces	399.99	349.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1686	\N	\N	Nerf Fortnite TS-R Tactical Shotgun	Nerf Fortnite TS-R Tactical Shotgun with 4 Official Nerf Fortnite Mega Darts	19.99	14.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
1687	\N	\N	Pokémon Trading Card Game: Sword & Shield Booster Pack	Pokémon Trading Card Game: Sword & Shield Booster Pack with 10 Cards	4.99	3.99	Pokémon	\N	\N	\N	Trading Cards	\N	\N
1688	\N	\N	Roblox Sharkbite Code Card	Roblox Sharkbite Code Card	10.00	8.00	Roblox	\N	\N	\N	Video Game Codes	\N	\N
1689	\N	\N	Beyblade Burst Surge Speed Storm Battle Set	Beyblade Burst Surge Speed Storm Battle Set with 2 Beyblades and 1 Stadium	29.99	24.99	Hasbro	\N	\N	\N	Beyblades	\N	\N
1690	\N	\N	Play-Doh Kitchen Creations Ultimate Pretend Play Kitchen	Play-Doh Kitchen Creations Ultimate Pretend Play Kitchen with 20 Accessories	49.99	39.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
1691	\N	\N	Nerf Fortnite Pump SG	Nerf Fortnite Pump SG with 4 Official Nerf Fortnite Mega Darts	29.99	24.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
1692	\N	\N	Minecraft Dungeons Jungle Awakens	Minecraft Dungeons Jungle Awakens for Xbox Series X, S, Xbox One, PS5, PS4, Nintendo Switch, and PC	19.99	14.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
1693	\N	\N	Hot Wheels Mario Kart Rainbow Road Race Set	Hot Wheels Mario Kart Rainbow Road Race Set with 1 Mario Kart Vehicle	39.99	29.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1694	\N	\N	Nintendo Switch Pro Controller	Nintendo Switch Pro Controller in Black	69.99	59.99	Nintendo	\N	\N	\N	Video Game Controllers	\N	\N
1695	\N	\N	LEGO Star Wars The Mandalorian The Razor Crest	LEGO Star Wars The Mandalorian The Razor Crest with 1023 Pieces	129.99	109.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1696	\N	\N	Fortnite V-Bucks Gift Card	Fortnite V-Bucks Gift Card with 1000 V-Bucks	10.00	8.00	Epic Games	\N	\N	\N	Video Game Currencies	\N	\N
1697	\N	\N	Roblox Gift Card	Roblox Gift Card with 800 Robux	10.00	8.00	Roblox	\N	\N	\N	Video Game Currencies	\N	\N
1698	\N	\N	Minecraft Java Edition	Minecraft Java Edition for PC	29.99	24.99	Mojang Studios	\N	\N	\N	Video Games	\N	\N
1699	\N	\N	Nerf Fortnite Victory Royale SR	Nerf Fortnite Victory Royale SR with 6 Official Nerf Fortnite Mega Darts	39.99	29.99	Nerf	\N	\N	\N	Nerf Guns	\N	\N
1700	\N	\N	LEGO Minecraft The Pig House	LEGO Minecraft The Pig House with 490 Pieces	29.99	24.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1701	\N	\N	Nintendo Switch Lite Carrying Case	Nintendo Switch Lite Carrying Case in Black	19.99	14.99	Nintendo	\N	\N	\N	Video Game Accessories	\N	\N
1702	\N	\N	Stuffed Teddy Bear	Plush soft brown bear with adorable eyes, perfect for cuddling.	14.99	11.99	CuddleCo	\N	\N	\N	Stuffed Animals	\N	\N
1703	\N	\N	Board Game: Monopoly Junior	Classic Monopoly gameplay designed for younger players.	19.99	15.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1704	\N	\N	Remote Control Car	Red Lamborghini-style RC car with working headlights.	29.99	24.99	SpeedRacer	\N	\N	\N	Remote Control Toys	\N	\N
1705	\N	\N	Slime Kit	Assortment of colorful slime with glitters, beads, and scents.	12.99	9.99	Gooey Creations	\N	\N	\N	Arts & Crafts	\N	\N
1706	\N	\N	Building Blocks Set	Large set of interlocking blocks in various shapes and colors.	24.99	19.99	MegaBlocks	\N	\N	\N	Building Toys	\N	\N
1707	\N	\N	Dollhouse	Pink and white dollhouse with 3 levels and multiple rooms.	49.99	39.99	DreamHouse	\N	\N	\N	Dolls & Accessories	\N	\N
1708	\N	\N	Science Experiment Kit	Hands-on experiments in chemistry, biology, and physics.	29.99	23.99	Explore Science	\N	\N	\N	Educational Toys	\N	\N
1709	\N	\N	Art Easel with Paper Roll	Double-sided easel with magnetic whiteboard and paper roll.	34.99	29.99	Art Central	\N	\N	\N	Arts & Crafts	\N	\N
1710	\N	\N	Nerf Blaster	Blue and orange blaster that fires soft darts.	19.99	16.99	Nerf	\N	\N	\N	Action Figures & Playsets	\N	\N
1711	\N	\N	Lego Star Wars Set	Buildable Millennium Falcon spaceship with minifigures.	39.99	31.99	Lego	\N	\N	\N	Building Toys	\N	\N
1712	\N	\N	Roblox Gift Card	Virtual currency for the popular online gaming platform.	20.00	20.00	Roblox	\N	\N	\N	Video Games	\N	\N
1713	\N	\N	Minecraft Sword and Shield Set	Foam sword and shield inspired by the Minecraft game.	14.99	11.99	Minecraft	\N	\N	\N	Action Figures & Playsets	\N	\N
1714	\N	\N	Unicorn Backpack	Sparkly pink backpack with a unicorn design.	19.99	15.99	GlitterGlam	\N	\N	\N	School Supplies	\N	\N
1715	\N	\N	Play Tent	Colorful play tent with roll-up door and mesh windows.	24.99	19.99	KidZone	\N	\N	\N	Outdoor Toys	\N	\N
1716	\N	\N	Squishy Ball	Stress-relieving ball in the shape of a fruit or animal.	6.99	4.99	SqueezeMe	\N	\N	\N	Fidget Toys	\N	\N
1717	\N	\N	Remote Control Airplane	Yellow and blue RC airplane with easy-to-fly controls.	39.99	31.99	AeroForce	\N	\N	\N	Remote Control Toys	\N	\N
1718	\N	\N	Frozen Elsa Doll	Detailed Elsa doll inspired by the Disney movie.	29.99	23.99	Disney	\N	\N	\N	Dolls & Accessories	\N	\N
1719	\N	\N	Rubik's Cube	Classic 3x3 Rubik's Cube in vibrant colors.	9.99	7.99	Rubik's	\N	\N	\N	Puzzles & Games	\N	\N
1720	\N	\N	Scooter	Pink and silver scooter with adjustable handlebars.	49.99	39.99	GlideX	\N	\N	\N	Outdoor Toys	\N	\N
1721	\N	\N	Board Game: Candy Land	Sweet-themed board game for young children.	14.99	11.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1722	\N	\N	Craft Supply Kit	Assortment of paper, markers, crayons, and scissors.	19.99	15.99	Art Studio	\N	\N	\N	Arts & Crafts	\N	\N
1723	\N	\N	Walkie Talkies Pair	2-way radios with a range of up to 1 mile.	24.99	19.99	TalkTalk	\N	\N	\N	Outdoor Toys	\N	\N
1724	\N	\N	Play Kitchen Set	Fully equipped kitchen playset with pretend appliances and accessories.	49.99	39.99	KidKraft	\N	\N	\N	Dolls & Accessories	\N	\N
1725	\N	\N	Musical Instrument: Ukulele	Small and beginner-friendly ukulele with nylon strings.	29.99	23.99	MusicMakers	\N	\N	\N	Musical Instruments	\N	\N
1726	\N	\N	Bath Bombs Gift Set	Set of scented and colorful bath bombs for relaxation.	19.99	15.99	Soak & Relax	\N	\N	\N	Bath Toys	\N	\N
1727	\N	\N	Glow Sticks Set	Assortment of glow sticks in different colors.	9.99	7.99	Neon Nights	\N	\N	\N	Outdoor Toys	\N	\N
1728	\N	\N	Stuffed Unicorn	Soft and cuddly unicorn plush with iridescent horn.	19.99	15.99	Dreamy Creatures	\N	\N	\N	Stuffed Animals	\N	\N
1729	\N	\N	Construction Toy Set	Building blocks with tools, vehicles, and construction pieces.	29.99	23.99	Builderz	\N	\N	\N	Building Toys	\N	\N
1730	\N	\N	Play Doh Set	Assortment of colorful Play Doh pots with molds and accessories.	14.99	11.99	Hasbro	\N	\N	\N	Arts & Crafts	\N	\N
1731	\N	\N	Nerf Darts Refill	Pack of 50 soft darts for Nerf blasters.	9.99	7.99	Nerf	\N	\N	\N	Action Figures & Playsets	\N	\N
1732	\N	\N	Makeup Kit for Kids	Non-toxic and hypoallergenic makeup for pretend play.	19.99	15.99	GlamGirl	\N	\N	\N	Dress Up & Pretend Play	\N	\N
1733	\N	\N	Jewelry Making Kit	Beads, string, and tools for creating custom jewelry.	14.99	11.99	BeadleMania	\N	\N	\N	Arts & Crafts	\N	\N
1734	\N	\N	Slime Recipe Book	Step-by-step recipes for making your own unique slime.	9.99	7.99	Slimey Secrets	\N	\N	\N	Arts & Crafts	\N	\N
1735	\N	\N	Board Game: Monopoly	Classic Monopoly gameplay for older children and adults.	29.99	23.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1736	\N	\N	Train Set with Tracks	Complete train set with tracks, engine, and carriages. Perfect for imaginative play.	19.99	14.99	Fisher-Price	\N	\N	\N	Trains	\N	\N
1737	\N	\N	Dollhouse with Furniture	Spacious dollhouse with multiple rooms and furniture. Perfect for pretend play.	29.99	24.99	Barbie	\N	\N	\N	Dollhouses	\N	\N
1738	\N	\N	Building Blocks	Set of colorful building blocks in various shapes and sizes. Perfect for developing fine motor skills.	14.99	10.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1739	\N	\N	Play Kitchen	Fully equipped play kitchen with stove, oven, sink, and accessories. Perfect for imaginative play.	49.99	39.99	Step2	\N	\N	\N	Pretend Play	\N	\N
1740	\N	\N	Arts and Crafts Set	Set of art supplies including markers, crayons, and paper. Perfect for creativity and self-expression.	19.99	16.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
1741	\N	\N	Ride-On Car	Battery-operated ride-on car with realistic features. Perfect for outdoor play.	99.99	79.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
1742	\N	\N	Play Tent	Spacious play tent with pop-up design. Perfect for indoor or outdoor play.	29.99	24.99	Melissa & Doug	\N	\N	\N	Play Tents	\N	\N
1743	\N	\N	Stuffed Animal	Soft and cuddly stuffed animal. Perfect for comfort and companionship.	14.99	10.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1744	\N	\N	Puzzle	Colorful puzzle with easy-to-assemble pieces. Perfect for developing problem-solving skills.	9.99	7.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1745	\N	\N	Board Game	Classic board game suitable for ages 5+. Perfect for family game nights.	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1746	\N	\N	Musical Instrument	Toy musical instrument that plays different sounds. Perfect for musical exploration.	14.99	10.99	VTech	\N	\N	\N	Musical Instruments	\N	\N
1747	\N	\N	Science Kit	Set of science experiments and activities. Perfect for budding scientists.	19.99	16.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1748	\N	\N	Construction Set	Set of building pieces that can be used to create different structures. Perfect for imaginative play.	29.99	24.99	LEGO	\N	\N	\N	Construction Toys	\N	\N
1749	\N	\N	Action Figure	Detailed action figure of a popular character. Perfect for imaginative play.	14.99	10.99	Marvel	\N	\N	\N	Action Figures	\N	\N
1750	\N	\N	Doll	Realistic doll with movable joints and accessories. Perfect for pretend play.	49.99	39.99	American Girl	\N	\N	\N	Dolls	\N	\N
1751	\N	\N	Toy Car	Die-cast toy car with realistic features. Perfect for vehicle enthusiasts.	5.99	4.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1752	\N	\N	Playmat	Soft and colorful playmat with interactive features. Perfect for tummy time and sensory development.	29.99	24.99	Skip Hop	\N	\N	\N	Playmats	\N	\N
1753	\N	\N	Dress-Up Set	Set of dress-up clothes and accessories. Perfect for imaginative play and self-expression.	19.99	16.99	Disney	\N	\N	\N	Dress-Up	\N	\N
1754	\N	\N	Electronic Learning Toy	Toy that teaches basic skills such as letters, numbers, and shapes. Perfect for early learning.	24.99	19.99	LeapFrog	\N	\N	\N	Electronic Learning Toys	\N	\N
1755	\N	\N	Bath Toy	Floating or squirting toy designed for bath time fun. Perfect for water play and sensory development.	9.99	7.99	Munchkin	\N	\N	\N	Bath Toys	\N	\N
1756	\N	\N	Outdoor Playset	Large outdoor playset with slides, swings, and climbing structures. Perfect for active play.	199.99	149.99	Little Tikes	\N	\N	\N	Outdoor Playsets	\N	\N
1757	\N	\N	Trampoline	Small trampoline suitable for indoor or outdoor use. Perfect for jumping and exercise.	99.99	79.99	JumpSport	\N	\N	\N	Trampolines	\N	\N
1758	\N	\N	Sandbox	Sandbox with lid and sand toys. Perfect for outdoor sensory play.	29.99	24.99	Step2	\N	\N	\N	Sandboxes	\N	\N
1759	\N	\N	Water Table	Water table with interactive features and accessories. Perfect for water play and sensory development.	39.99	34.99	Little Tikes	\N	\N	\N	Water Tables	\N	\N
1760	\N	\N	Toy Train	Battery-operated toy train with tracks and accessories. Perfect for imaginative play.	24.99	19.99	Thomas & Friends	\N	\N	\N	Toy Trains	\N	\N
1761	\N	\N	Toy Airplane	Toy airplane with sound and light effects. Perfect for imaginative play and aspiring pilots.	19.99	14.99	Fisher-Price	\N	\N	\N	Toy Airplanes	\N	\N
1762	\N	\N	Toy Rocket	Toy rocket with realistic features and sound effects. Perfect for imaginative play and aspiring astronauts.	24.99	19.99	Melissa & Doug	\N	\N	\N	Toy Rockets	\N	\N
1763	\N	\N	Toy Farm	Set of toy farm animals, vehicles, and accessories. Perfect for imaginative play and learning about farm life.	29.99	24.99	John Deere	\N	\N	\N	Toy Farms	\N	\N
1764	\N	\N	Toy Zoo	Set of toy zoo animals, habitats, and accessories. Perfect for imaginative play and learning about wildlife.	39.99	34.99	National Geographic	\N	\N	\N	Toy Zoos	\N	\N
1765	\N	\N	Toy Hospital	Set of toy medical equipment and accessories. Perfect for imaginative play and learning about healthcare.	29.99	24.99	Melissa & Doug	\N	\N	\N	Toy Hospitals	\N	\N
1766	\N	\N	Toy Fire Station	Set of toy fire trucks, firefighters, and accessories. Perfect for imaginative play and learning about firefighting.	34.99	29.99	Fisher-Price	\N	\N	\N	Toy Fire Stations	\N	\N
1767	\N	\N	Puzzle	100-piece puzzle of popular cartoon characters	14.99	9.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1768	\N	\N	Toy Police Station	Set of toy police cars, officers, and accessories. Perfect for imaginative play and learning about law enforcement.	34.99	29.99	Melissa & Doug	\N	\N	\N	Toy Police Stations	\N	\N
1769	\N	\N	Toy Grocery Store	Set of toy groceries, shopping carts, and accessories. Perfect for imaginative play and learning about shopping.	49.99	39.99	KidKraft	\N	\N	\N	Toy Grocery Stores	\N	\N
1770	\N	\N	Toy Restaurant	Set of toy restaurant furniture, food, and accessories. Perfect for imaginative play and learning about dining.	44.99	39.99	Melissa & Doug	\N	\N	\N	Toy Restaurants	\N	\N
1771	\N	\N	Toy Salon	Set of toy salon chairs, hairdryers, and accessories. Perfect for imaginative play and learning about hairstyling.	29.99	24.99	Barbie	\N	\N	\N	Toy Salons	\N	\N
1772	\N	\N	Stuffed Lion	Soft and cuddly stuffed lion with realistic facial features and a fluffy mane. Perfect for cuddling and imaginative play.	14.99	11.99	Plush & Co.	\N	\N	\N	Stuffed Animals	\N	\N
1773	\N	\N	Wooden Train Set	Classic wooden train set with brightly colored wooden tracks, trains, and accessories. Encourages imagination, motor skills, and spatial reasoning.	24.99	19.99	Thomas & Friends	\N	\N	\N	Train Sets	\N	\N
1774	\N	\N	Toy Car Garage	Multi-level toy car garage with ramps, elevators, and a helicopter pad. Includes a set of toy cars for imaginative play.	39.99	29.99	Little Tikes	\N	\N	\N	Playsets	\N	\N
1775	\N	\N	Dollhouse	Wooden dollhouse with three levels, multiple rooms, and furniture. Encourages imagination, social skills, and creativity.	49.99	39.99	Melissa & Doug	\N	\N	\N	Dollhouses	\N	\N
1776	\N	\N	Play Kitchen	Realistic play kitchen with stove, oven, sink, and refrigerator. Includes pots, pans, and play food for pretend play.	99.99	79.99	KidKraft	\N	\N	\N	Play Kitchens	\N	\N
1777	\N	\N	Art Easel	Double-sided art easel with magnetic whiteboard and paper roll holder. Includes markers, crayons, and paper for creative expression.	29.99	24.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1778	\N	\N	Toy Tool Set	Pretend play tool set with plastic hammer, wrench, screwdriver, and other tools. Encourages imagination, problem-solving, and fine motor skills.	19.99	14.99	Battat	\N	\N	\N	Toy Tools	\N	\N
1779	\N	\N	Building Blocks	Set of colorful plastic building blocks with different shapes and sizes. Encourages creativity, imagination, and spatial reasoning.	14.99	11.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1780	\N	\N	Play Tent	Pop-up play tent with fun designs and colors. Provides a cozy and imaginative play space for kids.	24.99	19.99	Melissa & Doug	\N	\N	\N	Tents	\N	\N
1781	\N	\N	Teddy Bear	Classic teddy bear with soft, cuddly fur and embroidered eyes. Perfect for comforting and pretend play.	19.99	14.99	Gund	\N	\N	\N	Stuffed Animals	\N	\N
1782	\N	\N	Balance Bike	Two-wheeled balance bike without pedals. Helps kids develop balance, coordination, and confidence.	79.99	64.99	Strider	\N	\N	\N	Bikes	\N	\N
1783	\N	\N	Sand Table	Sturdy plastic sand table with built-in sandbox and cover. Encourages sensory play, imagination, and fine motor skills.	39.99	29.99	Little Tikes	\N	\N	\N	Sandboxes	\N	\N
1784	\N	\N	Trampoline	Small indoor trampoline with a padded safety net. Provides exercise and entertainment for kids.	99.99	79.99	JumpSport	\N	\N	\N	Trampolines	\N	\N
1785	\N	\N	Water Table	Interactive water table with squirting toys, water jets, and a removable umbrella. Encourages sensory play and water exploration.	49.99	39.99	Step2	\N	\N	\N	Water Tables	\N	\N
1786	\N	\N	Board Game	Classic board game like Monopoly Junior or Candy Land. Encourages strategy, counting, and social interaction.	14.99	11.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1787	\N	\N	Doll Stroller	Sturdy doll stroller with a comfortable seat and adjustable handle. Perfect for pretend play and nurturing skills.	29.99	24.99	Corolle	\N	\N	\N	Doll Accessories	\N	\N
1788	\N	\N	Play Makeup Kit	Washable play makeup kit with pretend lipstick, eyeshadow, and nail polish. Encourages imagination and self-expression.	19.99	14.99	Crayola	\N	\N	\N	Play Cosmetics	\N	\N
1789	\N	\N	Craft Kit	Craft kit with materials like construction paper, scissors, glue, and markers. Encourages creativity, fine motor skills, and self-expression.	14.99	11.99	Crayola	\N	\N	\N	Craft Supplies	\N	\N
1790	\N	\N	Remote Control Car	Electric remote control car with rugged tires and a durable body. Provides entertainment and encourages problem-solving.	29.99	24.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
1791	\N	\N	Scooter	Two-wheeled scooter with an adjustable handlebar and a sturdy deck. Encourages balance, coordination, and outdoor play.	49.99	39.99	Razor	\N	\N	\N	Scooters	\N	\N
1792	\N	\N	Science Kit	Science kit with experiments and materials for exploring scientific concepts like magnets, air pressure, and more.	29.99	24.99	National Geographic	\N	\N	\N	Science & Nature	\N	\N
1793	\N	\N	Slime Kit	Slime kit with ingredients and instructions for making colorful, stretchy slime. Encourages creativity, sensory play, and scientific exploration.	14.99	11.99	Elmer's	\N	\N	\N	Craft Supplies	\N	\N
1794	\N	\N	Dress-Up Clothes	Set of dress-up clothes like princess gowns, firefighter uniforms, or animal costumes. Encourages imagination, role-playing, and self-expression.	29.99	24.99	Melissa & Doug	\N	\N	\N	Dress-Up & Pretend Play	\N	\N
1795	\N	\N	Playmat	Soft and colorful playmat with interactive features like crinkle paper, mirrors, and teething toys. Encourages sensory development and motor skills.	24.99	19.99	Skip Hop	\N	\N	\N	Baby Toys	\N	\N
1796	\N	\N	Musical Instrument Set	Set of musical instruments like a drum, xylophone, and tambourine. Encourages creativity, rhythm, and musical expression.	29.99	24.99	Melissa & Doug	\N	\N	\N	Musical Toys	\N	\N
1797	\N	\N	Construction Vehicle Set	Set of toy construction vehicles like excavators, dump trucks, and bulldozers. Encourages imagination, problem-solving, and fine motor skills.	19.99	14.99	Tonka	\N	\N	\N	Toy Vehicles	\N	\N
1798	\N	\N	Magnetic Tiles	Set of colorful magnetic tiles with different shapes and sizes. Encourages creativity, spatial reasoning, and problem-solving.	29.99	24.99	Magna-Tiles	\N	\N	\N	Building Blocks	\N	\N
1799	\N	\N	Robot Kit	Robot kit with parts and instructions for building and customizing a working robot. Encourages creativity, engineering skills, and problem-solving.	49.99	39.99	LEGO	\N	\N	\N	STEM Toys	\N	\N
1800	\N	\N	Puzzles	Set of puzzles with different themes and difficulty levels. Encourages problem-solving, spatial reasoning, and cognitive skills.	14.99	11.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1801	\N	\N	Art Supplies	Set of art supplies like markers, crayons, paintbrushes, and paper. Encourages creativity, imagination, and self-expression.	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1802	\N	\N	Educational Toy	Interactive educational toy that teaches concepts like colors, numbers, shapes, and sounds. Encourages learning and cognitive development.	29.99	24.99	LeapFrog	\N	\N	\N	Learning Toys	\N	\N
1803	\N	\N	Play Tent	Foldable play tent with tunnel	29.99	24.99	Melissa & Doug	\N	\N	\N	Play Tents	\N	\N
1804	\N	\N	Musical Instrument	Toy musical instrument like a xylophone, drum, or guitar. Encourages musical expression, rhythm, and creativity.	19.99	14.99	Melissa & Doug	\N	\N	\N	Musical Toys	\N	\N
1805	\N	\N	Playhouse	Indoor or outdoor playhouse with a fun design and interactive features. Provides a private and imaginative play space.	99.99	79.99	Step2	\N	\N	\N	Playhouses	\N	\N
1806	\N	\N	Tricycle	Three-wheeled tricycle with a sturdy frame and adjustable seat. Encourages balance, coordination, and outdoor play.	49.99	39.99	Radio Flyer	\N	\N	\N	Tricycles	\N	\N
1807	\N	\N	Action Figure, 12-inch, Batman	Highly detailed Batman action figure with realistic costume and accessories	19.99	14.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
1808	\N	\N	Doll, 18-inch, Barbie	Classic Barbie doll with long blonde hair and blue eyes	19.99	14.99	Mattel	\N	\N	\N	Dolls	\N	\N
1809	\N	\N	Playset, PAW Patrol, Adventure Bay Rescue Center	Multi-level playset with lights, sounds, and accessories	49.99	39.99	Spin Master	\N	\N	\N	Playsets	\N	\N
1810	\N	\N	Building Blocks, Mega Bloks, First Builders	Large, colorful building blocks for toddlers	14.99	9.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1811	\N	\N	Board Game, Monopoly Junior	Simplified version of Monopoly for younger players	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1812	\N	\N	Toy Car, Hot Wheels, '67 Camaro	Die-cast toy car with realistic details and working wheels	5.99	4.99	Hot Wheels	\N	\N	\N	Toy Cars	\N	\N
1813	\N	\N	Toy Train, Thomas & Friends, Percy	Motorized toy train with cargo car and track	29.99	24.99	Fisher-Price	\N	\N	\N	Toy Trains	\N	\N
1814	\N	\N	Stuffed Animal, Ty, Beanie Boo	Soft and cuddly stuffed animal with big eyes and a cute expression	9.99	7.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1815	\N	\N	Craft Kit, Crayola, Washable Sidewalk Chalk	Pack of 12 washable sidewalk chalk in bright colors	7.99	5.99	Crayola	\N	\N	\N	Craft Kits	\N	\N
1816	\N	\N	Play Dough, Play-Doh, 10-Pack	Non-toxic play dough in various colors	7.99	5.99	Hasbro	\N	\N	\N	Play Dough	\N	\N
1817	\N	\N	Science Kit, Thames & Kosmos, Kids First Chemistry	Hands-on science kit for kids aged 5-8	24.99	19.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
1818	\N	\N	Puzzle, Ravensburger, Disney Princess	100-piece puzzle featuring Disney Princesses	14.99	9.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1819	\N	\N	Book, Dr. Seuss, The Cat in the Hat	Classic children's book by Dr. Seuss	12.99	9.99	Random House	\N	\N	\N	Books	\N	\N
1820	\N	\N	Movie, Disney, Frozen II	Animated Disney movie sequel with catchy songs and lovable characters	19.99	14.99	Disney	\N	\N	\N	Movies	\N	\N
1821	\N	\N	Video Game, Nintendo Switch, Mario Kart 8 Deluxe	Racing game featuring Mario and friends	59.99	49.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1822	\N	\N	Scooter, Razor, A5 Lux Kick Scooter	Lightweight and durable kick scooter for kids aged 5+	99.99	79.99	Razor	\N	\N	\N	Scooters	\N	\N
1823	\N	\N	Dollhouse, KidKraft, Majestic Mansion	Large wooden dollhouse with multiple rooms and accessories	199.99	149.99	KidKraft	\N	\N	\N	Dollhouses	\N	\N
1824	\N	\N	Trampoline, JumpSport, 8-Foot Round Trampoline	Safe and sturdy trampoline for kids and adults	299.99	249.99	JumpSport	\N	\N	\N	Trampolines	\N	\N
1825	\N	\N	Swing Set, Backyard Discovery, SkyFort II	Large swing set with multiple swings, a slide, and a fort	799.99	699.99	Backyard Discovery	\N	\N	\N	Swing Sets	\N	\N
1826	\N	\N	Inflatable Pool, Intex, Easy Set Pool	Quick and easy to set up inflatable pool for summer fun	79.99	59.99	Intex	\N	\N	\N	Inflatable Pools	\N	\N
1827	\N	\N	Water Gun, Super Soaker, Hydro Cannon	Powerful water gun with long range and high capacity	19.99	14.99	Nerf	\N	\N	\N	Water Guns	\N	\N
1828	\N	\N	Kite, In the Breeze, Rainbow Delta Kite	Colorful and easy-to-fly delta kite	14.99	9.99	In the Breeze	\N	\N	\N	Kites	\N	\N
1829	\N	\N	Bubbles, Gazillion Bubbles, Giant Bubble Wand	Produces hundreds of giant bubbles at once	9.99	7.99	Gazillion Bubbles	\N	\N	\N	Bubbles	\N	\N
1830	\N	\N	Chalkboard, Melissa & Doug, Magnetic Chalkboard Easel	Double-sided chalkboard easel with magnetic letters and numbers	49.99	39.99	Melissa & Doug	\N	\N	\N	Chalkboards	\N	\N
1831	\N	\N	Art Set, Crayola, My First Washable Art Kit	Non-toxic art supplies for toddlers	19.99	14.99	Crayola	\N	\N	\N	Art Sets	\N	\N
1832	\N	\N	Musical Instrument, Melissa & Doug, Pound & Tap Bench	Wooden musical instrument with hammers and xylophone	29.99	24.99	Melissa & Doug	\N	\N	\N	Musical Instruments	\N	\N
1833	\N	\N	Play Kitchen, KidKraft, Uptown Elite Kitchen	Interactive play kitchen with realistic appliances and accessories	199.99	149.99	KidKraft	\N	\N	\N	Play Kitchens	\N	\N
1834	\N	\N	Ride-On Toy, Little Tikes, Cozy Coupe	Classic ride-on toy car with a removable floor	79.99	59.99	Little Tikes	\N	\N	\N	Ride-On Toys	\N	\N
1835	\N	\N	Sandpit, Step2, Naturally Playful Sandbox	Large sandpit with a built-in cover	129.99	99.99	Step2	\N	\N	\N	Sandpits	\N	\N
1836	\N	\N	Tent, Eureka!, Kohana 2-Person Tent	Lightweight and compact tent for camping or backyard sleepovers	99.99	79.99	Eureka!	\N	\N	\N	Tents	\N	\N
1837	\N	\N	Sleeping Bag, Coleman, Sundome Sleeping Bag	Warm and comfortable sleeping bag for camping	49.99	39.99	Coleman	\N	\N	\N	Sleeping Bags	\N	\N
1838	\N	\N	Headlamp, Petzl, Tikka Headlamp	Compact and bright headlamp for outdoor activities	49.99	39.99	Petzl	\N	\N	\N	Headlamps	\N	\N
1839	\N	\N	Backpack, Osprey, Talon 22 Backpack	Durable and comfortable backpack for hiking or school	99.99	79.99	Osprey	\N	\N	\N	Backpacks	\N	\N
1840	\N	\N	Water Bottle, Hydro Flask, 32 oz Wide Mouth Bottle	Insulated water bottle that keeps drinks cold or hot	39.99	29.99	Hydro Flask	\N	\N	\N	Water Bottles	\N	\N
1841	\N	\N	Camping Chair, REI Co-op, Camp X Chair	Compact and comfortable camping chair	39.99	29.99	REI Co-op	\N	\N	\N	Camping Chairs	\N	\N
1842	\N	\N	Toy Truck	Large red toy truck with working headlights and sounds	24.99	19.99	Tonka	\N	\N	\N	Trucks	\N	\N
1843	\N	\N	Dollhouse	Three-story dollhouse with furniture and accessories	49.99	39.99	Barbie	\N	\N	\N	Dolls	\N	\N
1844	\N	\N	Action Figure	12-inch action figure of popular superhero	19.99	14.99	Marvel	\N	\N	\N	Action Figures	\N	\N
1845	\N	\N	Building Blocks	Set of 100 colorful building blocks	14.99	9.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1846	\N	\N	Musical Instrument	Toy piano with 25 keys and working speakers	29.99	24.99	Playskool	\N	\N	\N	Musical Toys	\N	\N
1847	\N	\N	Stuffed Animal	Soft and cuddly stuffed teddy bear	19.99	14.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1848	\N	\N	Board Game	Classic board game for 2-4 players	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1849	\N	\N	Craft Kit	Craft kit with materials for making slime	12.99	9.99	Elmer's	\N	\N	\N	Craft Kits	\N	\N
1850	\N	\N	Science Kit	Science kit with experiments and activities	24.99	19.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1851	\N	\N	Video Game	Video game for Nintendo Switch	59.99	49.99	Nintendo	\N	\N	\N	Video Games	\N	\N
1852	\N	\N	Building Set	Construction set with bricks and instructions	49.99	39.99	LEGO	\N	\N	\N	Building Sets	\N	\N
1853	\N	\N	Toy Train	Electric train set with tracks and accessories	99.99	79.99	Lionel	\N	\N	\N	Toy Trains	\N	\N
1854	\N	\N	Art Supplies	Set of crayons, markers, and paper	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1855	\N	\N	Musical Instrument	Toy drum with drumsticks	14.99	9.99	First Act	\N	\N	\N	Musical Toys	\N	\N
1856	\N	\N	Stuffed Animal	Plush dog toy with realistic barking sound	19.99	14.99	Petstages	\N	\N	\N	Stuffed Animals	\N	\N
1857	\N	\N	Board Game	Strategy board game for 2-4 players	49.99	39.99	Catan	\N	\N	\N	Board Games	\N	\N
1858	\N	\N	Craft Kit	Jewelry-making kit with beads and string	19.99	14.99	Creativity for Kids	\N	\N	\N	Craft Kits	\N	\N
1859	\N	\N	Science Kit	Chemistry kit with experiments and chemicals	29.99	24.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
1860	\N	\N	Video Game	Video game for Xbox One	59.99	49.99	Microsoft	\N	\N	\N	Video Games	\N	\N
1861	\N	\N	Puzzle	300-piece puzzle of famous painting	24.99	19.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1862	\N	\N	Play Tent	Pop-up play tent with glow-in-the-dark stars	29.99	24.99	Playhouse	\N	\N	\N	Play Tents	\N	\N
1863	\N	\N	Ride-On Toy	Balance bike for toddlers	89.99	79.99	Strider	\N	\N	\N	Ride-On Toys	\N	\N
1864	\N	\N	Building Set	Magnetic building set with colorful blocks	49.99	39.99	Magformers	\N	\N	\N	Building Sets	\N	\N
1865	\N	\N	Toy Train	Wooden train set with tracks and accessories	59.99	49.99	Thomas & Friends	\N	\N	\N	Toy Trains	\N	\N
1866	\N	\N	Art Supplies	Set of paints, brushes, and canvas	24.99	19.99	Arteza	\N	\N	\N	Art Supplies	\N	\N
1867	\N	\N	Musical Instrument	Electronic keyboard with 61 keys	99.99	79.99	Yamaha	\N	\N	\N	Musical Toys	\N	\N
1868	\N	\N	Stuffed Animal	Giant stuffed giraffe toy	49.99	39.99	Wild Republic	\N	\N	\N	Stuffed Animals	\N	\N
1869	\N	\N	Board Game	Educational board game for 2-4 players	29.99	24.99	ThinkFun	\N	\N	\N	Board Games	\N	\N
1870	\N	\N	Craft Kit	Sewing kit with fabric, thread, and needles	19.99	14.99	Simplicity	\N	\N	\N	Craft Kits	\N	\N
1871	\N	\N	Science Kit	Physics kit with experiments and equipment	49.99	39.99	Elenco	\N	\N	\N	Science Kits	\N	\N
1872	\N	\N	Video Game	Video game for PlayStation 4	59.99	49.99	Sony	\N	\N	\N	Video Games	\N	\N
1873	\N	\N	Action Figure, Superman	Superhero action figure with movable joints and realistic details	14.99	9.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
1874	\N	\N	Doll, Barbie Dreamhouse	Large dollhouse with multiple rooms and accessories	29.99	19.99	Barbie	\N	\N	\N	Dolls	\N	\N
1875	\N	\N	Building Blocks, LEGO City Police Station	Police station building set with minifigures and vehicles	39.99	29.99	LEGO	\N	\N	\N	Building Blocks	\N	\N
1876	\N	\N	Game, Monopoly Junior	Simplified version of the classic board game for younger players	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1877	\N	\N	Puzzle, Paw Patrol	Paw Patrol themed puzzle with 100 pieces	9.99	6.99	Spin Master	\N	\N	\N	Puzzles	\N	\N
1878	\N	\N	Stuffed Animal, Disney Mickey Mouse	Soft and cuddly Mickey Mouse plush toy	19.99	14.99	Disney	\N	\N	\N	Stuffed Animals	\N	\N
1879	\N	\N	Art Set, Crayola Super Art Case	Large art set with crayons, markers, and paper	29.99	24.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1880	\N	\N	Musical Instrument, Toy Piano	Small toy piano with 25 keys	19.99	14.99	Melissa & Doug	\N	\N	\N	Musical Instruments	\N	\N
1881	\N	\N	Science Kit, National Geographic Ultimate Slime Kit	Slime-making kit with instructions and ingredients	24.99	19.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1882	\N	\N	Vehicle, Hot Wheels Monster Truck	Large monster truck toy with oversized wheels	14.99	9.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1883	\N	\N	Figure Set, Star Wars The Mandalorian	Set of action figures from the Star Wars series	29.99	24.99	Star Wars	\N	\N	\N	Figure Sets	\N	\N
1884	\N	\N	Doll, American Girl Doll	18-inch doll with accessories and outfits	129.99	99.99	American Girl	\N	\N	\N	Dolls	\N	\N
1885	\N	\N	Building Blocks, Mega Bloks First Builders	Large building blocks for toddlers	19.99	14.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1886	\N	\N	Game, Candy Land	Classic board game with colorful characters and sweet treats	14.99	9.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1887	\N	\N	Puzzle, Disney Princess	Disney Princess themed puzzle with 50 pieces	9.99	6.99	Disney	\N	\N	\N	Puzzles	\N	\N
1888	\N	\N	Stuffed Animal, Ty Beanie Boo	Cute and cuddly beanie baby animal	9.99	6.99	Ty	\N	\N	\N	Stuffed Animals	\N	\N
1889	\N	\N	Art Set, Crayola Washable Crayons	Pack of washable crayons in bright colors	9.99	6.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1890	\N	\N	Musical Instrument, Toy Drum Set	Small toy drum set with drumsticks	14.99	9.99	Melissa & Doug	\N	\N	\N	Musical Instruments	\N	\N
1891	\N	\N	Science Kit, Thames & Kosmos Crystal Growing Lab	Crystal-growing kit with instructions and materials	29.99	24.99	Thames & Kosmos	\N	\N	\N	Science Kits	\N	\N
1892	\N	\N	Vehicle, Matchbox Car Set	Set of 10 small toy cars	9.99	6.99	Matchbox	\N	\N	\N	Vehicles	\N	\N
1893	\N	\N	Figure Set, Marvel Avengers	Set of action figures from the Marvel Avengers series	24.99	19.99	Marvel	\N	\N	\N	Figure Sets	\N	\N
1894	\N	\N	Doll, Our Generation Doll	18-inch doll with accessories and outfits	119.99	89.99	Our Generation	\N	\N	\N	Dolls	\N	\N
1895	\N	\N	Building Blocks, LEGO Friends Heartlake City Park	Park building set with minifigures and accessories	39.99	29.99	LEGO	\N	\N	\N	Building Blocks	\N	\N
1896	\N	\N	Game, Jenga Classic	Classic stacking game with wooden blocks	19.99	14.99	Hasbro	\N	\N	\N	Board Games	\N	\N
1897	\N	\N	Puzzle, Paw Patrol Big Floor Puzzle	Large floor puzzle with Paw Patrol characters	19.99	14.99	Spin Master	\N	\N	\N	Puzzles	\N	\N
1898	\N	\N	Stuffed Animal, Gund Teddy Bear	Soft and cuddly teddy bear	29.99	24.99	Gund	\N	\N	\N	Stuffed Animals	\N	\N
1899	\N	\N	Art Set, Crayola Inspiration Art Case	Large art set with various art supplies	39.99	34.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1900	\N	\N	Musical Instrument, Toy Ukulele	Small toy ukulele with nylon strings	19.99	14.99	Melissa & Doug	\N	\N	\N	Musical Instruments	\N	\N
1901	\N	\N	Science Kit, National Geographic Kids First Microscope	Microscope for beginners with slides and instructions	29.99	24.99	National Geographic	\N	\N	\N	Science Kits	\N	\N
1902	\N	\N	Vehicle, Hot Wheels Stunt Track Set	Stunt track set with ramps and loops	29.99	24.99	Hot Wheels	\N	\N	\N	Vehicles	\N	\N
1903	\N	\N	Figure Set, Star Wars The Clone Wars	Set of action figures from the Star Wars series	29.99	24.99	Star Wars	\N	\N	\N	Figure Sets	\N	\N
1904	\N	\N	Doll, Baby Alive Sweet Spoonfuls Baby	Interactive baby doll that eats and drinks	29.99	24.99	Hasbro	\N	\N	\N	Dolls	\N	\N
1905	\N	\N	Building Blocks, Mega Bloks First Builders Farm	Farm-themed building set for toddlers	14.99	9.99	Mega Bloks	\N	\N	\N	Building Blocks	\N	\N
1906	\N	\N	Game, Monopoly Deal	Card game based on the classic Monopoly board game	9.99	6.99	Hasbro	\N	\N	\N	Card Games	\N	\N
1907	\N	\N	Puzzle, Disney Cars Puzzle	Disney Cars themed puzzle with 24 pieces	9.99	6.99	Disney	\N	\N	\N	Puzzles	\N	\N
1908	\N	\N	Stuffed Animal, Webkinz Plush	Interactive plush toy that comes with a virtual pet	19.99	14.99	Webkinz	\N	\N	\N	Stuffed Animals	\N	\N
1909	\N	\N	Art Set, Crayola Washable Markers	Pack of washable markers in bright colors	9.99	6.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1910	\N	\N	Musical Instrument, Toy Guitar	Small toy guitar with plastic strings	14.99	9.99	Melissa & Doug	\N	\N	\N	Musical Instruments	\N	\N
1911	\N	\N	Stuffed Animal Dog	Soft and cuddly plush dog with realistic features, perfect for snuggling.	19.99	14.99	Paw Patrol	\N	\N	\N	Plush Toys	\N	\N
1912	\N	\N	Action Figure Superhero	Articulated action figure with realistic details and accessories.	14.99	9.99	Marvel	\N	\N	\N	Action Figures	\N	\N
1913	\N	\N	Building Blocks Set	Colorful and durable building blocks in various shapes and sizes.	29.99	24.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1914	\N	\N	Board Game	Fun and educational board game for 2-4 players.	19.99	14.99	Candy Land	\N	\N	\N	Board Games	\N	\N
1915	\N	\N	Card Game	Exciting and challenging card game for all ages.	9.99	7.99	Uno	\N	\N	\N	Card Games	\N	\N
1916	\N	\N	Craft Kit	Complete craft kit with everything needed to create a fun and unique project.	14.99	10.99	Crayola	\N	\N	\N	Craft Kits	\N	\N
1917	\N	\N	Doll	Beautiful and stylish doll with realistic features and accessories.	19.99	14.99	Barbie	\N	\N	\N	Dolls	\N	\N
1918	\N	\N	Educational Toy	Interactive toy that encourages learning and development.	24.99	19.99	LeapFrog	\N	\N	\N	Educational Toys	\N	\N
1919	\N	\N	Electronic Game	Handheld or console game with exciting and engaging gameplay.	39.99	29.99	Nintendo	\N	\N	\N	Electronic Games	\N	\N
1920	\N	\N	Figure Playset	Set of figurines and accessories for imaginative play.	19.99	14.99	Star Wars	\N	\N	\N	Figure Playsets	\N	\N
1921	\N	\N	Musical Instrument	Toy musical instrument that encourages creativity and musical exploration.	14.99	10.99	Fisher-Price	\N	\N	\N	Musical Instruments	\N	\N
1922	\N	\N	Outdoor Toy	Active and fun toy for playing outdoors.	19.99	14.99	Nerf	\N	\N	\N	Outdoor Toys	\N	\N
1923	\N	\N	Pretend Play Toy	Toy that encourages imaginative play and social development.	14.99	10.99	Melissa & Doug	\N	\N	\N	Pretend Play Toys	\N	\N
1924	\N	\N	Puzzle	Challenging and fun puzzle that helps develop problem-solving skills.	9.99	7.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1925	\N	\N	Remote Control Toy	Toy that can be controlled remotely for interactive play.	19.99	14.99	Hot Wheels	\N	\N	\N	Remote Control Toys	\N	\N
1926	\N	\N	Ride-On Toy	Toy vehicle that can be ridden by children.	49.99	39.99	Power Wheels	\N	\N	\N	Ride-On Toys	\N	\N
1927	\N	\N	Sensory Toy	Toy that stimulates the senses and promotes relaxation.	9.99	7.99	Slinky	\N	\N	\N	Sensory Toys	\N	\N
1928	\N	\N	STEM Toy	Toy that encourages science, technology, engineering, and math learning.	29.99	24.99	LEGO	\N	\N	\N	STEM Toys	\N	\N
1929	\N	\N	Stuffed Animal Cat	Soft and cuddly plush cat with realistic features, perfect for snuggling.	19.99	14.99	Hello Kitty	\N	\N	\N	Plush Toys	\N	\N
1930	\N	\N	Action Figure Princess	Articulated action figure with realistic details and accessories.	14.99	9.99	Disney	\N	\N	\N	Action Figures	\N	\N
1931	\N	\N	Building Blocks Set	Colorful and durable building blocks in various shapes and sizes.	24.99	19.99	Mega Bloks	\N	\N	\N	Building Toys	\N	\N
1932	\N	\N	Board Game	Fun and educational board game for 2-4 players.	19.99	14.99	Monopoly Junior	\N	\N	\N	Board Games	\N	\N
1933	\N	\N	Card Game	Exciting and challenging card game for all ages.	9.99	7.99	Pokemon	\N	\N	\N	Card Games	\N	\N
1934	\N	\N	Craft Kit	Complete craft kit with everything needed to create a fun and unique project.	14.99	10.99	Klutz	\N	\N	\N	Craft Kits	\N	\N
1935	\N	\N	Doll	Beautiful and stylish doll with realistic features and accessories.	29.99	24.99	American Girl	\N	\N	\N	Dolls	\N	\N
1936	\N	\N	Educational Toy	Interactive toy that encourages learning and development.	24.99	19.99	VTech	\N	\N	\N	Educational Toys	\N	\N
1937	\N	\N	Electronic Game	Handheld or console game with exciting and engaging gameplay.	39.99	29.99	PlayStation	\N	\N	\N	Electronic Games	\N	\N
1938	\N	\N	Figure Playset	Set of figurines and accessories for imaginative play.	19.99	14.99	My Little Pony	\N	\N	\N	Figure Playsets	\N	\N
1939	\N	\N	Musical Instrument	Toy musical instrument that encourages creativity and musical exploration.	14.99	10.99	Casio	\N	\N	\N	Musical Instruments	\N	\N
1940	\N	\N	Outdoor Toy	Active and fun toy for playing outdoors.	24.99	19.99	Razor	\N	\N	\N	Outdoor Toys	\N	\N
1941	\N	\N	Pretend Play Toy	Toy that encourages imaginative play and social development.	14.99	10.99	Melissa & Doug	\N	\N	\N	Pretend Play Toys	\N	\N
1942	\N	\N	Puzzle	Challenging and fun puzzle that helps develop problem-solving skills.	9.99	7.99	Ravensburger	\N	\N	\N	Puzzles	\N	\N
1943	\N	\N	Remote Control Toy	Toy that can be controlled remotely for interactive play.	19.99	14.99	Air Hogs	\N	\N	\N	Remote Control Toys	\N	\N
1944	\N	\N	Ride-On Toy	Toy vehicle that can be ridden by children.	49.99	39.99	Razor	\N	\N	\N	Ride-On Toys	\N	\N
1945	\N	\N	Sensory Toy	Toy that stimulates the senses and promotes relaxation.	9.99	7.99	Play-Doh	\N	\N	\N	Sensory Toys	\N	\N
1946	\N	\N	STEM Toy	Toy that encourages science, technology, engineering, and math learning.	29.99	24.99	Thames & Kosmos	\N	\N	\N	STEM Toys	\N	\N
1947	\N	\N	Star Wars BB-8 Droid	Interactive droid with sound effects and lightsabers, perfect for young Jedi	24.99	19.99	Star Wars	\N	\N	\N	Toys for Boys	\N	\N
1948	\N	\N	LEGO Star Wars Millennium Falcon	Buildable model of the iconic spaceship from the Star Wars movies	79.99	59.99	LEGO	\N	\N	\N	Toys for Boys	\N	\N
1949	\N	\N	Hatchimals Surprise	Interactive toy that hatches into a cute creature	59.99	49.99	Hatchimals	\N	\N	\N	Toys for Girls	\N	\N
1950	\N	\N	Nerf Fortnite Bas-R Blaster	Toy blaster with electronic sounds and lights, inspired by the popular video game	19.99	14.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
1951	\N	\N	LOL Surprise! OMG Styling Head	Styling head with 30+ surprises to create different looks	29.99	24.99	LOL Surprise!	\N	\N	\N	Toys for Girls	\N	\N
1952	\N	\N	Barbie Dreamhouse	Playset that includes a house, furniture, and accessories	99.99	79.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
1953	\N	\N	Hot Wheels City Ultimate Garage	Playset with 9 levels and multiple tracks for Hot Wheels cars	129.99	99.99	Hot Wheels	\N	\N	\N	Toys for Boys	\N	\N
1954	\N	\N	Construction Building Blocks	Large set of colorful building blocks for creative play	24.99	21.99	Mega Bloks	\N	\N	\N	Building	\N	\N
1955	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Maker	Playset that includes a pretend ice cream maker and accessories	19.99	14.99	Play-Doh	\N	\N	\N	Toys for Girls	\N	\N
1956	\N	\N	Mega Construx Halo UNSC Pelican Dropship	Buildable model of the UNSC Pelican dropship from the Halo video game series	29.99	24.99	Mega Construx	\N	\N	\N	Toys for Boys	\N	\N
1957	\N	\N	Crayola Ultimate Crayon Collection	Set of 150 crayons in a variety of colors	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1958	\N	\N	Nerf Fortnite SMG-E Blaster	Toy blaster with electronic sounds and lights, inspired by the popular video game	29.99	24.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
1959	\N	\N	LEGO Harry Potter Hogwarts Great Hall	Buildable model of the Great Hall from the Harry Potter movies	99.99	79.99	LEGO	\N	\N	\N	Toys for Boys	\N	\N
1960	\N	\N	Barbie DreamCamper	Playset that includes a camper van, furniture, and accessories	89.99	69.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
1961	\N	\N	Hot Wheels Monster Trucks Mega Wrex	Giant monster truck with oversized wheels and lights	24.99	19.99	Hot Wheels	\N	\N	\N	Toys for Boys	\N	\N
1962	\N	\N	Play-Doh Kitchen Creations Ultimate Burger Maker	Playset that includes a pretend burger maker and accessories	19.99	14.99	Play-Doh	\N	\N	\N	Toys for Girls	\N	\N
1963	\N	\N	Mega Construx Halo Infinite Banshee	Buildable model of the Banshee from the Halo Infinite video game	24.99	19.99	Mega Construx	\N	\N	\N	Toys for Boys	\N	\N
1964	\N	\N	Crayola Washable Markers	Set of 10 washable markers in bright colors	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1965	\N	\N	Nerf Fortnite TS-R Blaster	Toy blaster with electronic sounds and lights, inspired by the popular video game	19.99	14.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
1966	\N	\N	LEGO Friends Heartlake City Hotel	Buildable model of a hotel with multiple rooms and accessories	79.99	59.99	LEGO	\N	\N	\N	Toys for Girls	\N	\N
1967	\N	\N	Barbie Fashionistas Doll	Fashion doll with a variety of styles and accessories	9.99	7.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
1968	\N	\N	Hot Wheels 5-Alarm Raceway	Playset with a racetrack and multiple obstacles	29.99	24.99	Hot Wheels	\N	\N	\N	Toys for Boys	\N	\N
1969	\N	\N	Play-Doh Kitchen Creations Ultimate Pizza Oven	Playset that includes a pretend pizza oven and accessories	19.99	14.99	Play-Doh	\N	\N	\N	Toys for Girls	\N	\N
1970	\N	\N	Mega Construx Pokemon Squirtle	Buildable model of the Squirtle Pokemon character	14.99	11.99	Mega Construx	\N	\N	\N	Toys for Boys	\N	\N
1971	\N	\N	Crayola Construction Paper	Pack of 50 sheets of construction paper in a variety of colors	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1972	\N	\N	Nerf Elite 2.0 Phoenix	Toy blaster with electronic sounds and lights	29.99	24.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
1973	\N	\N	LEGO City Police Station	Buildable model of a police station with multiple rooms and accessories	99.99	79.99	LEGO	\N	\N	\N	Toys for Boys	\N	\N
1974	\N	\N	Barbie Dreamtopia Mermaid Doll	Fashion doll with a mermaid tail and accessories	14.99	11.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
1975	\N	\N	Hot Wheels Super Ultimate Garage	Playset with multiple levels, tracks, and parking spaces	149.99	119.99	Hot Wheels	\N	\N	\N	Toys for Boys	\N	\N
1976	\N	\N	Play-Doh Kitchen Creations Ultimate Frosting Station	Playset that includes a pretend frosting station and accessories	19.99	14.99	Play-Doh	\N	\N	\N	Toys for Girls	\N	\N
1977	\N	\N	Mega Construx Pokemon Pikachu	Buildable model of the Pikachu Pokemon character	14.99	11.99	Mega Construx	\N	\N	\N	Toys for Boys	\N	\N
1978	\N	\N	Crayola Washable Sidewalk Chalk	Pack of 64 washable sidewalk chalk sticks in a variety of colors	9.99	7.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
1979	\N	\N	Nerf Elite 2.0 Commander RD-6	Toy blaster with electronic sounds and lights	29.99	24.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
1980	\N	\N	LEGO Friends Heartlake City Park	Buildable model of a park with multiple areas and accessories	49.99	39.99	LEGO	\N	\N	\N	Toys for Girls	\N	\N
1981	\N	\N	Barbie Club Chelsea Camper	Playset that includes a camper van, furniture, and accessories	19.99	14.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
1982	\N	\N	Hot Wheels Monster Trucks Race Ace	Giant monster truck with oversized wheels and lights	24.99	19.99	Hot Wheels	\N	\N	\N	Toys for Boys	\N	\N
1983	\N	\N	Play-Doh Ice Cream Creations Ultimate Ice Cream Truck	Playset that includes a pretend ice cream truck and accessories	29.99	24.99	Play-Doh	\N	\N	\N	Toys for Girls	\N	\N
1984	\N	\N	Nerf Fortnite BASR-L Blaster	The Nerf Fortnite BASR-L is a bolt-action blaster that fires Elite Darts. It's inspired by the blaster used in the Fortnite video game and features realistic details.	29.99	24.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
1985	\N	\N	LEGO Star Wars The Child Building Kit	Recreate the adorable character from the hit Disney+ series The Mandalorian with the LEGO Star Wars The Child building kit. The set includes 1,073 pieces and features authentic details, such as the Child's green skin, large ears, and brown coat.	79.99	69.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1986	\N	\N	Barbie Dreamhouse Adventures Camper	Take Barbie on adventures with the Barbie Dreamhouse Adventures Camper playset. The camper features a slide-out kitchen, bathroom, and sleeping area, as well as a working sunroof and headlights.	49.99	39.99	Barbie	\N	\N	\N	Dolls and Accessories	\N	\N
1987	\N	\N	Hot Wheels Monster Trucks Demo Double Destruction Playset	Crush cars and perform epic stunts with the Hot Wheels Monster Trucks Demo Double Destruction playset. The set includes two monster trucks and a launcher that sends them crashing into each other.	24.99	19.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
1988	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck Playset	Create and serve delicious Play-Doh ice cream with the Play-Doh Kitchen Creations Ultimate Ice Cream Truck playset. The set includes a truck, ice cream machine, molds, and a variety of Play-Doh colors.	29.99	24.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
1989	\N	\N	Melissa & Doug Wooden Peg Puzzle Farm	Learn about farm animals and develop fine motor skills with the Melissa & Doug Wooden Peg Puzzle Farm. The puzzle features 12 wooden pegs that fit into corresponding holes on a wooden farm board.	19.99	14.99	Melissa & Doug	\N	\N	\N	Puzzles	\N	\N
1990	\N	\N	Magna-Tiles Clear Colors 100-Piece Set	Build and create amazing structures with the Magna-Tiles Clear Colors 100-Piece Set. The set includes 100 magnetic tiles in a variety of shapes and colors that can be connected in endless ways.	49.99	39.99	Magna-Tiles	\N	\N	\N	Building Toys	\N	\N
1991	\N	\N	Crayola Ultimate Crayon Collection	Express yourself with the Crayola Ultimate Crayon Collection. The set includes 150 crayons in a variety of bright and vibrant colors, as well as metallic, glitter, and glow-in-the-dark crayons.	29.99	24.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
1992	\N	\N	Interactive Robot Pet	Robot pet that responds to voice commands and touch	49.99	44.99	Robo Pets	\N	\N	\N	Pets	\N	\N
1993	\N	\N	LEGO Classic Creative Brick Box	Build anything you can imagine with the LEGO Classic Creative Brick Box. The set includes 592 bricks in a variety of colors and shapes that can be used to create buildings, vehicles, animals, and much more.	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
1994	\N	\N	Play-Doh Super Color Pack	Get creative with the Play-Doh Super Color Pack. The pack includes 30 cans of Play-Doh in a variety of bright and vibrant colors, as well as metallic and glitter colors.	19.99	14.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
1995	\N	\N	UNO Card Game	Enjoy classic card game fun with the UNO Card Game. The set includes 108 cards in four different colors and two special wild cards.	4.99	3.99	UNO	\N	\N	\N	Card Games	\N	\N
1996	\N	\N	Monopoly Junior Board Game	Introduce your child to the classic board game Monopoly with the Monopoly Junior Board Game. The game is designed for 2-4 players ages 5 and up and features simplified rules and a smaller board.	19.99	14.99	Monopoly	\N	\N	\N	Board Games	\N	\N
1997	\N	\N	Operation Board Game	Test your surgical skills with the Operation Board Game. The game includes a patient with removable body parts, tweezers, and a spinner that determines which body part you must remove.	19.99	14.99	Operation	\N	\N	\N	Board Games	\N	\N
1998	\N	\N	Candy Land Board Game	Take a sweet journey through Candy Land with the Candy Land Board Game. The game is designed for 2-4 players ages 3 and up and features a colorful board and candy-themed pieces.	14.99	9.99	Candy Land	\N	\N	\N	Board Games	\N	\N
1999	\N	\N	Chutes and Ladders Board Game	Race to the finish line in the Chutes and Ladders Board Game. The game is designed for 2-4 players ages 3 and up and features a game board with ladders and chutes that can help or hinder your progress.	14.99	9.99	Chutes and Ladders	\N	\N	\N	Board Games	\N	\N
2000	\N	\N	Connect Four Game	Try to get four of your colored discs in a row in the Connect Four Game. The game is designed for 2 players ages 6 and up and features a grid and two sets of colored discs.	9.99	7.99	Connect Four	\N	\N	\N	Games of Skill	\N	\N
2001	\N	\N	Pictionary Air Game	Draw in the air and guess what your teammates are drawing in the Pictionary Air Game. The game includes a special pen that you can use to draw in the air, as well as a deck of cards with words and phrases to draw.	19.99	14.99	Pictionary	\N	\N	\N	Games of Skill	\N	\N
2002	\N	\N	Jenga Game	Stack the wooden blocks and try not to knock them down in the Jenga Game. The game is designed for 2 or more players ages 6 and up and features 54 wooden blocks.	9.99	7.99	Jenga	\N	\N	\N	Games of Skill	\N	\N
2003	\N	\N	Twister Game	Get tangled up in the Twister Game. The game is designed for 2 or more players ages 6 and up and features a mat with colored circles that players must place their hands and feet on.	14.99	9.99	Twister	\N	\N	\N	Games of Skill	\N	\N
2004	\N	\N	Hungry Hungry Hippos Game	Feed your hungry hippos as many marbles as you can in the Hungry Hungry Hippos Game. The game is designed for 2-4 players ages 4 and up and features a game board with four hippo heads that open and close their mouths.	19.99	14.99	Hungry Hungry Hippos	\N	\N	\N	Games of Skill	\N	\N
2005	\N	\N	Simon Game	Follow the lights and sounds in the Simon Game. The game is designed for 1 or more players ages 8 and up and features a game unit with four colored buttons that light up and make sounds.	14.99	9.99	Simon	\N	\N	\N	Games of Skill	\N	\N
2006	\N	\N	Etch A Sketch	Draw and erase your creations over and over again with the Etch A Sketch. The toy features a screen that you can draw on with a stylus, and you can erase your drawings by shaking the toy.	19.99	14.99	Etch A Sketch	\N	\N	\N	Toys for Creativity	\N	\N
2007	\N	\N	Crayola Washable Markers	Color and create with the Crayola Washable Markers. The set includes 50 markers in a variety of bright and vibrant colors that are washable from skin and most clothing.	9.99	7.99	Crayola	\N	\N	\N	Arts and Crafts	\N	\N
2008	\N	\N	Play-Doh Modeling Compound	Get creative with the Play-Doh Modeling Compound. The set includes 4 cans of Play-Doh in different colors that you can mold, shape, and squish.	4.99	3.99	Play-Doh	\N	\N	\N	Arts and Crafts	\N	\N
2009	\N	\N	Kinetic Sand	Create and build with the Kinetic Sand. The sand is made from 98% sand and 2% magic, and it sticks to itself and not to you.	9.99	7.99	Kinetic Sand	\N	\N	\N	Arts and Crafts	\N	\N
2010	\N	\N	Slime	Get messy and creative with the Slime. The slime is made from a variety of ingredients, including glue, water, and food coloring, and it can be stretched, squeezed, and squished.	4.99	3.99	Slime	\N	\N	\N	Arts and Crafts	\N	\N
2011	\N	\N	LEGO Friends Friendship House	Build and create your own adventures with the LEGO Friends Friendship House. The set includes 730 pieces and features a three-story house with a kitchen, living room, bedroom, and bathroom.	79.99	69.99	LEGO	\N	\N	\N	Building Toys	\N	\N
2012	\N	\N	Barbie Dreamhouse	Imagine and create your own stories with the Barbie Dreamhouse. The set includes three stories, eight rooms, and over 70 accessories.	199.99	149.99	Barbie	\N	\N	\N	Dolls and Accessories	\N	\N
2013	\N	\N	Hot Wheels Ultimate Garage	Park and display your Hot Wheels cars in the Hot Wheels Ultimate Garage. The set features six levels, a spiral track, and a car elevator.	79.99	69.99	Hot Wheels	\N	\N	\N	Toy Vehicles	\N	\N
2014	\N	\N	Nerf Fortnite SP-L Elite Dart Blaster	Fire Elite Darts up to 75 feet with the Nerf Fortnite SP-L Elite Dart Blaster. The blaster is inspired by the blaster used in the Fortnite video game and features realistic details.	24.99	19.99	Nerf	\N	\N	\N	Toy Guns	\N	\N
2015	\N	\N	Transformers Bumblebee Cyberverse Adventures Action Figure	Transform Bumblebee from a robot to a car with the Transformers Bumblebee Cyberverse Adventures Action Figure. The figure is approximately 5 inches tall and features movie-inspired details.	19.99	14.99	Transformers	\N	\N	\N	Action Figures	\N	\N
2016	\N	\N	Paw Patrol Lookout Tower Playset	Join the Paw Patrol pups on their adventures with the Paw Patrol Lookout Tower Playset. The set includes a tower with a working elevator, a vehicle, and four pup figures.	49.99	39.99	Paw Patrol	\N	\N	\N	Playsets	\N	\N
2017	\N	\N	Peppa Pig Peppa's Adventures Playset	Explore Peppa Pig's world with the Peppa Pig Peppa's Adventures Playset. The set includes a house with a kitchen, living room, bedroom, and bathroom, as well as Peppa Pig, George, and Mummy Pig figures.	29.99	24.99	Peppa Pig	\N	\N	\N	Playsets	\N	\N
2018	\N	\N	PJ Masks Headquarters Playset	Become a superhero with the PJ Masks Headquarters Playset. The set includes a headquarters with a working elevator, a vehicle, and three superhero figures.	49.99	39.99	PJ Masks	\N	\N	\N	Playsets	\N	\N
2019	\N	\N	Blue Lightning RC Car	Remote control car with high speed and advanced suspension system	29.99	24.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
2020	\N	\N	Pink Sparkle Unicorn Plush	Soft and cuddly unicorn plush toy with shimmering mane and tail	19.99	16.99	Aurora	\N	\N	\N	Plush	\N	\N
2021	\N	\N	Superhero Action Figure Set	Set of 5 superhero action figures with realistic details and articulation	34.99	29.99	DC Comics	\N	\N	\N	Action Figures	\N	\N
2022	\N	\N	Princess Castle Playset	Detailed castle playset with multiple rooms and accessories	39.99	34.99	Disney Princess	\N	\N	\N	Dolls	\N	\N
2023	\N	\N	Nerf Blaster	Foam dart blaster with long range and accuracy	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
2024	\N	\N	Barbie Fashion Doll	Stylish Barbie doll with multiple outfits and accessories	24.99	21.99	Barbie	\N	\N	\N	Dolls	\N	\N
2025	\N	\N	Minecraft Creeper Plush	Soft and huggable plush toy based on the popular video game character	19.99	16.99	Mojang	\N	\N	\N	Plush	\N	\N
2026	\N	\N	Star Wars Lightsaber	Replica lightsaber with realistic sound effects and light	34.99	29.99	Hasbro	\N	\N	\N	Lightsabers	\N	\N
2027	\N	\N	Hot Wheels Track Builder	Set of track pieces and accessories for building custom car race tracks	29.99	24.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
2028	\N	\N	My Little Pony Playset	Playset featuring ponies, accessories, and a castle	39.99	34.99	My Little Pony	\N	\N	\N	Dolls	\N	\N
2029	\N	\N	LEGO City Police Station	Detailed police station playset with multiple rooms and accessories	49.99	44.99	LEGO	\N	\N	\N	Building	\N	\N
2030	\N	\N	Frozen Elsa Doll	Elsa doll with detailed costume and accessories	29.99	24.99	Disney Frozen	\N	\N	\N	Dolls	\N	\N
2031	\N	\N	Play-Doh Kitchen Creations	Play-Doh set with kitchen tools and ingredients for creative play	19.99	16.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
2032	\N	\N	PJ Masks Catboy Figure	Action figure of Catboy from the popular TV show	14.99	12.99	PJ Masks	\N	\N	\N	Action Figures	\N	\N
2033	\N	\N	Paw Patrol Lookout Tower	Playset featuring the Paw Patrol lookout tower and vehicles	49.99	44.99	Paw Patrol	\N	\N	\N	Pets	\N	\N
2034	\N	\N	Hot Wheels Monster Trucks	Set of monster truck toys with oversized tires and realistic details	24.99	21.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
2035	\N	\N	L.O.L. Surprise! Doll	Collectible doll with multiple layers of surprises	19.99	16.99	MGA Entertainment	\N	\N	\N	Dolls	\N	\N
2036	\N	\N	Kinetic Sand Bucket	Play sand that is moldable and flows like liquid	14.99	12.99	Kinetic Sand	\N	\N	\N	Sensory	\N	\N
2037	\N	\N	Transformers Optimus Prime Figure	Convertible Optimus Prime figure that transforms from robot to truck	39.99	34.99	Hasbro	\N	\N	\N	Action Figures	\N	\N
2038	\N	\N	Roblox Adopt Me! Pet Set	Set of virtual pet toys based on the popular Roblox game	24.99	21.99	Roblox	\N	\N	\N	Pets	\N	\N
2039	\N	\N	LOL Surprise! OMG Doll	Fashionable OMG doll with accessories and multiple surprises	29.99	24.99	MGA Entertainment	\N	\N	\N	Dolls	\N	\N
2040	\N	\N	Play-Doh Ice Cream Truck	Playset featuring an ice cream truck and accessories for creative play	29.99	24.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
2041	\N	\N	Crayola Super Tips Washable Markers	Set of vibrant washable markers for drawing and coloring	12.99	10.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
2042	\N	\N	Shopkins Shoppies Doll	Collectible doll with unique style and accessories	14.99	12.99	Shopkins	\N	\N	\N	Dolls	\N	\N
2043	\N	\N	Minecraft Creeper Headband	Headband with a 3D Creeper design from the popular video game	14.99	12.99	Mojang	\N	\N	\N	Accessories	\N	\N
2044	\N	\N	Star Wars Stormtrooper Helmet	Replica Stormtrooper helmet with realistic details and sounds	39.99	34.99	Hasbro	\N	\N	\N	Accessories	\N	\N
2045	\N	\N	Fortnite Llama Plush	Soft and cuddly plush toy based on the popular video game character	19.99	16.99	Epic Games	\N	\N	\N	Plush	\N	\N
2046	\N	\N	Nerf Fortnite RL	Foam dart blaster inspired by the popular Fortnite video game	29.99	24.99	Nerf	\N	\N	\N	Blasters	\N	\N
2047	\N	\N	Super Mario Odyssey Cap	Adjustable cap with the iconic Super Mario design	19.99	16.99	Nintendo	\N	\N	\N	Accessories	\N	\N
2048	\N	\N	Disney Frozen Singing Elsa Doll	Elsa doll that sings Let It Go and other songs	29.99	24.99	Disney Frozen	\N	\N	\N	Dolls	\N	\N
2049	\N	\N	Hot Wheels Stunt Track	Set of track pieces and accessories for building custom car stunt tracks	39.99	34.99	Hot Wheels	\N	\N	\N	Cars	\N	\N
2050	\N	\N	Melissa & Doug Wooden Activity Cube	Activity cube with multiple sides of interactive play	34.99	29.99	Melissa & Doug	\N	\N	\N	Educational	\N	\N
2051	\N	\N	Crayola Creativity Case	Carrying case filled with art supplies for drawing, painting, and more	29.99	24.99	Crayola	\N	\N	\N	Arts & Crafts	\N	\N
2052	\N	\N	Star Wars Mandalorian Lego Set	LEGO set featuring the Mandalorian warrior and his ship	49.99	44.99	LEGO	\N	\N	\N	Building	\N	\N
2053	\N	\N	Drone with Camera	Drone with 4K camera, 1080p video, 12MP still images, 20-minute flight time	199.99	159.99	Parrot	\N	\N	\N	Toys for Boys	\N	\N
2054	\N	\N	Remote Control Car	1:18 scale remote control car with full-function controls, 2.4GHz technology	99.99	79.99	Traxxas	\N	\N	\N	Toys for Boys	\N	\N
2055	\N	\N	Science Kit	100-piece science kit with experiments in physics, chemistry, and biology	39.99	29.99	National Geographic	\N	\N	\N	Educational Toys	\N	\N
2056	\N	\N	Board Game	Strategy board game for 2-4 players, ages 10 and up	29.99	19.99	Hasbro	\N	\N	\N	Games	\N	\N
2057	\N	\N	Dollhouse	Three-story dollhouse with 12 rooms and furniture	199.99	149.99	Melissa & Doug	\N	\N	\N	Toys for Girls	\N	\N
2058	\N	\N	Unicorn Stuffed Animal	Soft and cuddly unicorn stuffed animal with a pink mane and tail	24.99	19.99	Aurora	\N	\N	\N	Stuffed Animals	\N	\N
2059	\N	\N	Art Set	100-piece art set with crayons, markers, pencils, and paint	29.99	19.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
2060	\N	\N	Building Blocks	500-piece building block set with different shapes and colors	39.99	29.99	Mega Bloks	\N	\N	\N	Toys for Boys	\N	\N
2061	\N	\N	Nerf Gun	Electric Nerf gun with rotating barrel and 10 darts	34.99	24.99	Hasbro	\N	\N	\N	Toys for Boys	\N	\N
2062	\N	\N	Slime Kit	Make your own slime with this kit that includes glue, glitter, and food coloring	19.99	14.99	Elmer's	\N	\N	\N	Science Toys	\N	\N
2063	\N	\N	Play Tent	Pop-up play tent with a castle design	39.99	29.99	Melissa & Doug	\N	\N	\N	Toys for Girls	\N	\N
2064	\N	\N	Princess Dress	Pink princess dress with a tiara and wand	49.99	39.99	Disney	\N	\N	\N	Dress-Up Clothes	\N	\N
2065	\N	\N	Superhero Cape	Red superhero cape with a mask and gloves	29.99	19.99	Rubie's Costume Co.	\N	\N	\N	Dress-Up Clothes	\N	\N
2066	\N	\N	Toy Kitchen	Play kitchen with a stove, oven, and refrigerator	199.99	149.99	Little Tikes	\N	\N	\N	Toys for Girls	\N	\N
2067	\N	\N	Tool Set	10-piece tool set with a hammer, screwdriver, and wrench	29.99	19.99	Stanley	\N	\N	\N	Educational Toys	\N	\N
2068	\N	\N	Walkie-Talkies	Two-way walkie-talkies with a range of up to 2 miles	39.99	29.99	Motorola	\N	\N	\N	Toys for Boys	\N	\N
2069	\N	\N	Water Gun	Super soaker water gun with a capacity of 1 gallon	24.99	19.99	Nerf	\N	\N	\N	Water Toys	\N	\N
2070	\N	\N	Bath Bombs	Fizzing bath bombs with different scents and colors	19.99	14.99	Lush	\N	\N	\N	Bath Toys	\N	\N
2071	\N	\N	Play Dough	12-pack of play dough in different colors	19.99	14.99	Play-Doh	\N	\N	\N	Arts & Crafts	\N	\N
2072	\N	\N	Magic Kit	50-piece magic kit with tricks and illusions	29.99	19.99	David Blaine	\N	\N	\N	Educational Toys	\N	\N
2073	\N	\N	Craft Kit	Jewelry-making kit with beads, wire, and pliers	19.99	14.99	Klutz	\N	\N	\N	Arts & Crafts	\N	\N
2074	\N	\N	Book	Adventure book for ages 10 and up	14.99	9.99	Rick Riordan	\N	\N	\N	Books	\N	\N
2075	\N	\N	Legos	1000-piece Lego set with a space theme	49.99	39.99	Lego	\N	\N	\N	Toys for Boys	\N	\N
2076	\N	\N	Barbie Doll	Barbie doll with a pink dress and accessories	29.99	19.99	Barbie	\N	\N	\N	Toys for Girls	\N	\N
2077	\N	\N	Stuffed Animal	Soft and cuddly teddy bear	24.99	19.99	Teddy Bear	\N	\N	\N	Stuffed Animals	\N	\N
2078	\N	\N	Slime	Pre-made slime in a variety of colors and scents	9.99	7.99	Nickelodeon	\N	\N	\N	Toys for Girls	\N	\N
2079	\N	\N	Action Figure	Superhero action figure	19.99	14.99	Marvel	\N	\N	\N	Toys for Boys	\N	\N
2080	\N	\N	Play Mat	Large play mat with a city design	49.99	39.99	Melissa & Doug	\N	\N	\N	Toys for Boys	\N	\N
2081	\N	\N	Nerf Darts	50-pack of Nerf darts	14.99	9.99	Nerf	\N	\N	\N	Toys for Boys	\N	\N
2082	\N	\N	Playhouse	Plastic playhouse with a slide and swing	199.99	149.99	Little Tikes	\N	\N	\N	Toys for Girls	\N	\N
2083	\N	\N	Board Game	Family board game for 2-4 players	29.99	19.99	Hasbro	\N	\N	\N	Games	\N	\N
2084	\N	\N	Building Blocks	200-piece building block set with different shapes and colors	19.99	14.99	Mega Bloks	\N	\N	\N	Toys for Boys	\N	\N
2085	\N	\N	Stuffed Animal	Soft and cuddly cat stuffed animal	19.99	14.99	Aurora	\N	\N	\N	Stuffed Animals	\N	\N
2086	\N	\N	Magic Tricks	100-piece magic tricks set	49.99	39.99	David Blaine	\N	\N	\N	Educational Toys	\N	\N
2087	\N	\N	Science Kit	Chemistry kit with 25 experiments	39.99	29.99	National Geographic	\N	\N	\N	Educational Toys	\N	\N
2088	\N	\N	Play Kitchen	Wooden play kitchen with a stove, oven, and refrigerator	299.99	249.99	Melissa & Doug	\N	\N	\N	Toys for Girls	\N	\N
2089	\N	\N	Remote Control Stunt Car	This high-speed RC stunt car performs 360-degree spins and flips with ease. Its durable construction and off-road tires make it perfect for adventurous kids.	24.99	19.99	Speed Demons	\N	\N	\N	Remote Control Cars	\N	\N
2090	\N	\N	Glow-in-the-Dark Slime Kit	Create your own glowing slime with this fun and educational kit. Includes slime base, glow powder, and glitter.	12.99	9.99	Mad Science	\N	\N	\N	Science Kits	\N	\N
2091	\N	\N	Interactive Dinosaur Puzzle	This 3D dinosaur puzzle comes to life with augmented reality technology. Kids can scan the puzzle pieces with their smartphone or tablet to see the dinosaurs roar and move.	19.99	14.99	Dino Discovery	\N	\N	\N	Puzzles	\N	\N
2092	\N	\N	Craft Bead Jewelry Making Set	Design and create your own unique jewelry with this colorful bead set. Includes beads, string, and instructions.	14.99	10.99	Bead Bonanza	\N	\N	\N	Arts & Crafts	\N	\N
2093	\N	\N	Walkie-Talkie Set	Stay connected with your friends on adventures with this two-way walkie-talkie set. Features a long range and clear sound.	29.99	24.99	Adventure Gear	\N	\N	\N	Outdoor Toys	\N	\N
2094	\N	\N	Stuffed Unicorn with Rainbow Mane	This cuddly unicorn is perfect for bedtime snuggles. Its soft fur and vibrant rainbow mane will delight any child.	19.99	14.99	Dreamland Toys	\N	\N	\N	Stuffed Animals	\N	\N
2095	\N	\N	Building Block Racetrack	Construct your own racetrack with these colorful building blocks. Includes cars, ramps, and obstacles.	24.99	19.99	Block City	\N	\N	\N	Building Toys	\N	\N
2096	\N	\N	Educational Microscope	Explore the microscopic world with this easy-to-use microscope. Perfect for budding scientists.	39.99	29.99	Science Safari	\N	\N	\N	Science Kits	\N	\N
2097	\N	\N	Art Projector	Trace and draw your favorite images with this portable art projector. Includes slides with different patterns and designs.	29.99	24.99	Creative Corner	\N	\N	\N	Arts & Crafts	\N	\N
2098	\N	\N	Play Kitchen Set	Cook up imaginary meals with this realistic play kitchen set. Includes a stove, oven, sink, and accessories.	49.99	39.99	Kiddy Chef	\N	\N	\N	Pretend Play	\N	\N
2099	\N	\N	Magnetic Building Tiles	Build 3D structures with these magnetic building tiles. Encourages creativity and problem-solving skills.	34.99	29.99	MagnaPlay	\N	\N	\N	Building Toys	\N	\N
2100	\N	\N	STEM Robotics Kit	Learn the basics of robotics with this hands-on kit. Includes motors, sensors, and building blocks.	49.99	39.99	RoboTech	\N	\N	\N	STEM Toys	\N	\N
2101	\N	\N	Glow-in-the-Dark Star Projector	Create a magical starry night in your child's room with this glow-in-the-dark star projector.	19.99	14.99	Dreamy Nights	\N	\N	\N	Night Lights	\N	\N
2102	\N	\N	Interactive Coding Robot	Introduce your child to coding with this interactive robot. Teaches basic programming concepts through fun games.	44.99	34.99	Codecademy Kids	\N	\N	\N	STEM Toys	\N	\N
2103	\N	\N	Art Supply Super Set	Unlock your child's creativity with this comprehensive art supply set. Includes paints, markers, crayons, and more.	29.99	24.99	Artastic	\N	\N	\N	Arts & Crafts	\N	\N
2104	\N	\N	Water Balloon Launcher	Cool off on hot days with this water balloon launcher. Shoots water balloons up to 100 feet.	14.99	10.99	SoakZone	\N	\N	\N	Outdoor Toys	\N	\N
2105	\N	\N	Giant Bubble Wand	Create enormous bubbles with this giant bubble wand. Perfect for outdoor fun and imaginative play.	9.99	7.99	Bubble Bonanza	\N	\N	\N	Outdoor Toys	\N	\N
2106	\N	\N	DIY Slime Factory	Make your own slime from scratch with this slime factory. Includes all the ingredients and tools needed.	19.99	14.99	Slime Time	\N	\N	\N	Science Kits	\N	\N
2107	\N	\N	Remote Control Plane	Soar through the skies with this remote control plane. Its lightweight design and easy controls make it perfect for beginners.	39.99	29.99	Airborne Adventures	\N	\N	\N	Remote Control Toys	\N	\N
2108	\N	\N	Interactive Dollhouse	Create endless imaginative stories with this interactive dollhouse. Comes with dolls, furniture, and accessories.	49.99	39.99	Dreamy Dollhouses	\N	\N	\N	Pretend Play	\N	\N
2109	\N	\N	Musical Instrument Set	Introduce your child to the joy of music with this musical instrument set. Includes a guitar, drum, and keyboard.	29.99	24.99	Musical Moments	\N	\N	\N	Musical Toys	\N	\N
2110	\N	\N	Nerf Blaster	Engage in exciting Nerf battles with this powerful blaster. Shoots darts up to 75 feet.	24.99	19.99	Nerf Nation	\N	\N	\N	Outdoor Toys	\N	\N
2111	\N	\N	Remote Control Helicopter	Take flight with this remote control helicopter. Its agile design and stable flight make it perfect for indoor and outdoor adventures.	34.99	29.99	Helicopter Havoc	\N	\N	\N	Remote Control Toys	\N	\N
2112	\N	\N	Craft Paper Airplane Kit	Design and fly your own paper airplanes with this fun and educational kit. Includes paper, templates, and instructions.	12.99	9.99	Paper Pilots	\N	\N	\N	Arts & Crafts	\N	\N
2113	\N	\N	Interactive Coding Game	Learn the basics of coding through interactive games and puzzles. Perfect for kids who love technology.	29.99	24.99	Code Quest	\N	\N	\N	STEM Toys	\N	\N
2114	\N	\N	Crystal Growing Kit	Grow your own crystals with this mesmerizing kit. Includes crystal powder, seeds, and instructions.	19.99	14.99	Crystal Kingdom	\N	\N	\N	Science Kits	\N	\N
2115	\N	\N	Personalized Name Puzzle	Help your child learn their name with this personalized name puzzle. Made from durable wood and brightly colored letters.	14.99	10.99	Name Play	\N	\N	\N	Puzzles	\N	\N
2116	\N	\N	Animal Safari Playset	embark on an African safari adventure with this realistic playset. Includes animal figurines, a jeep, and a tent.	39.99	29.99	Safari Adventures	\N	\N	\N	Pretend Play	\N	\N
2117	\N	\N	Build-Your-Own Mini City	Construct your own miniature city with these building blocks. Includes houses, cars, and trees.	29.99	24.99	Block City Jr.	\N	\N	\N	Building Toys	\N	\N
2118	\N	\N	Remote Control Tank	Command your own army with this remote control tank. Its realistic design and powerful motors make it perfect for imaginative battles.	39.99	29.99	Tank Time	\N	\N	\N	Remote Control Toys	\N	\N
2119	\N	\N	Science Fair Project Kit	Prepare for your next science fair with this comprehensive project kit. Includes materials, instructions, and a display board.	29.99	24.99	Science Fair Central	\N	\N	\N	Science Kits	\N	\N
2120	\N	\N	Interactive Coding Cube	Introduce your child to coding in a fun and engaging way with this interactive coding cube.	34.99	29.99	Code Cube	\N	\N	\N	STEM Toys	\N	\N
2121	\N	\N	DIY Terrarium Kit	Create your own miniature ecosystem with this DIY terrarium kit. Includes a glass jar, soil, plants, and instructions.	19.99	14.99	Nature Nook	\N	\N	\N	Science Kits	\N	\N
2122	\N	\N	Personalized Storybook	Create a unique and special storybook featuring your child's name and adventures.	29.99	24.99	Storytime Magic	\N	\N	\N	Books	\N	\N
2123	\N	\N	Radio-Controlled Stunt Car	1:18 scale remote-controlled stunt car with high-performance motor and 4-wheel drive for extreme stunts	19.99	14.99	X-Speed	\N	\N	\N	Remote Control Cars	\N	\N
2124	\N	\N	Nerf Fortnite BASR-L Blaster	Full-size blaster replica with rotating 6-dart drum, slam fire, and scope	29.99	24.99	Nerf	\N	\N	\N	Nerf Blasters	\N	\N
2125	\N	\N	LEGO Star Wars The Mandalorian's Razor Crest	75292-piece LEGO set featuring the Razor Crest spaceship and iconic characters from the Mandalorian series	139.99	119.99	LEGO	\N	\N	\N	Building Toys	\N	\N
2126	\N	\N	Barbie Dreamhouse Adventures Campervan	Convertible campervan playset with sleeping area, kitchen, and accessories	49.99	39.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
2127	\N	\N	Hot Wheels Monster Trucks Mega Wrex	Large-scale Monster Truck with oversized wheels and realistic sound effects	24.99	19.99	Hot Wheels	\N	\N	\N	Monster Trucks	\N	\N
2128	\N	\N	Nintendo Switch Lite	Portable gaming console with a 5.5-inch touch screen and access to the Nintendo Switch library	199.99	179.99	Nintendo	\N	\N	\N	Video Games	\N	\N
2129	\N	\N	Beyblade Burst Evolution Sword Valtryek V4	High-performance Beyblade with a 4-layer design and rubber blade for enhanced performance	19.99	14.99	Beyblade	\N	\N	\N	Beyblades	\N	\N
2130	\N	\N	Melissa & Doug Wooden Dollhouse	Sturdy wooden dollhouse with multiple rooms, furniture, and accessories	99.99	89.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
2131	\N	\N	Minecraft Dungeons Hero Edition	Action-adventure game set in the Minecraft universe with unique dungeons, characters, and weapons	29.99	24.99	Mojang	\N	\N	\N	Video Games	\N	\N
2132	\N	\N	Roblox SharkBite Code Card	Code card for the Roblox SharkBite game, which unlocks exclusive content and bonuses	19.99	14.99	Roblox	\N	\N	\N	Roblox Cards	\N	\N
2133	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Play-Doh playset featuring an ice cream truck, molds, and accessories	29.99	24.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
2134	\N	\N	Crayola Inspiration Ultimate Art Case	Deluxe art case with over 140 Crayola art supplies, including markers, crayons, and paper	49.99	39.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
2135	\N	\N	Nerf Elite 2.0 Commander RD-6 Blaster	Foam dart blaster with a rotating 6-dart drum, tactical rails, and slam fire	29.99	24.99	Nerf	\N	\N	\N	Nerf Blasters	\N	\N
2136	\N	\N	L.O.L. Surprise! O.M.G. House of Surprises	Multi-level dollhouse with over 85 surprises and exclusive dolls	109.99	99.99	L.O.L. Surprise!	\N	\N	\N	Dolls & Accessories	\N	\N
2137	\N	\N	Hot Wheels City Super Twist & Race Track Set	Epic track set with multiple levels, loops, and a motorized booster	59.99	49.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
2138	\N	\N	LEGO Creator 3in1 Space Shuttle Adventure	3-in-1 LEGO set featuring a space shuttle, satellite, and lunar lander	49.99	39.99	LEGO	\N	\N	\N	Building Toys	\N	\N
2139	\N	\N	Fortnite Victory Royale Series Meowscles Action Figure	7-inch action figure of the popular Fortnite character Meowscles	19.99	14.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
2140	\N	\N	Barbie Rainbow High Convertible Corvette	Convertible sports car with realistic details, working headlights, and a Barbie doll	49.99	39.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
2141	\N	\N	Nintendo Switch Ring Fit Adventure	Fitness game that combines exercise with adventure and mini-games	79.99	69.99	Nintendo	\N	\N	\N	Video Games	\N	\N
2142	\N	\N	Melissa & Doug Wooden Activity Table	Sturdy wooden table with multiple activity stations and accessories	79.99	69.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
2143	\N	\N	Minecraft Dungeons Jungle Awakens DLC	Expansion pack for Minecraft Dungeons, featuring new levels, enemies, and weapons	19.99	14.99	Mojang	\N	\N	\N	Video Games	\N	\N
2144	\N	\N	Play-Doh Dino Crew Stegosaurus	Play-Doh playset featuring a Stegosaurus mold, accessories, and 2 cans of Play-Doh	14.99	11.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
2145	\N	\N	Crayola Color Wonder Mess-Free Coloring Kit	Mess-free coloring kit with special markers and paper that only show color on designated areas	19.99	14.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
2146	\N	\N	Nerf Elite 2.0 Phoenix CS-6 Blaster	Compact blaster with a 6-dart clip, pump-action, and tactical rails	24.99	19.99	Nerf	\N	\N	\N	Nerf Blasters	\N	\N
2147	\N	\N	L.O.L. Surprise! Tweens Fashion Doll - Max Wonder	15-inch fashion doll with stylish clothes, accessories, and a collectible trading card	29.99	24.99	L.O.L. Surprise!	\N	\N	\N	Dolls & Accessories	\N	\N
2148	\N	\N	Hot Wheels Criss Cross Crash Track Set	Interactive track set with multiple loops, intersections, and a motorized booster	49.99	39.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
2149	\N	\N	LEGO Star Wars TIE Fighter Attack	75300-piece LEGO set featuring a TIE fighter and 3 minifigures	39.99	34.99	LEGO	\N	\N	\N	Building Toys	\N	\N
2150	\N	\N	Fortnite Pop! Games - Midas	Vinyl Pop! figure of the popular Fortnite character Midas	10.99	8.99	Fortnite	\N	\N	\N	Action Figures	\N	\N
2151	\N	\N	Barbie Fashionistas Ultimate Closet	Playset with a wardrobe, clothing, accessories, and a Barbie doll	49.99	39.99	Barbie	\N	\N	\N	Dolls & Accessories	\N	\N
2152	\N	\N	Nintendo Switch Fortnite Special Edition	Limited edition Nintendo Switch console with Fortnite-themed design and exclusive content	299.99	269.99	Nintendo	\N	\N	\N	Video Games	\N	\N
2153	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Magnetic dress-up doll with interchangeable clothing and accessories	19.99	14.99	Melissa & Doug	\N	\N	\N	Pretend Play	\N	\N
2154	\N	\N	Play-Doh Super Color Pack	Value pack with 20 cans of Play-Doh in various colors	19.99	14.99	Play-Doh	\N	\N	\N	Play-Doh	\N	\N
2155	\N	\N	Crayola Twistables Colored Pencils	Twistable colored pencils with vibrant colors and smooth writing	14.99	11.99	Crayola	\N	\N	\N	Art Supplies	\N	\N
2156	\N	\N	Nerf Fortnite Pump SG	Pump-action shotgun blaster inspired by the Fortnite video game	24.99	19.99	Nerf	\N	\N	\N	Nerf Blasters	\N	\N
2157	\N	\N	L.O.L. Surprise! Remix Hair Flip Surprise	Playset with 15 surprises, including a doll with surprise hair transformation	14.99	11.99	L.O.L. Surprise!	\N	\N	\N	Dolls & Accessories	\N	\N
2158	\N	\N	Hot Wheels Mario Kart Circuit Track Set	Track set inspired by the Mario Kart video game, featuring iconic characters and obstacles	49.99	39.99	Hot Wheels	\N	\N	\N	Track Sets	\N	\N
2159	\N	\N	Remote Control Stunt Car	High-performance remote control stunt car with durable construction, advanced suspension system, and sleek design.	29.99	19.99	Speedster	\N	\N	\N	Toys	\N	\N
2160	\N	\N	Nerf Rival Apollo XV-700 Blaster	Powerful and accurate Nerf Rival blaster with high-impact rounds and rotating magazine.	24.99	16.99	Nerf	\N	\N	\N	Toys	\N	\N
2161	\N	\N	Beyblade Burst Surge Speedstorm Riptide	High-performance Beyblade with unique Riptide energy layer and spring-loaded driver.	14.99	9.99	Takara Tomy	\N	\N	\N	Toys	\N	\N
2162	\N	\N	LEGO Star Wars: The Mandalorian's Razor Crest	Detailed LEGO model of the iconic spacecraft from The Mandalorian series.	149.99	129.99	LEGO	\N	\N	\N	Toys	\N	\N
2163	\N	\N	Barbie Dreamhouse	Spacious and interactive Barbie dollhouse with multiple rooms, furniture, and accessories.	199.99	159.99	Barbie	\N	\N	\N	Toys	\N	\N
2164	\N	\N	Hot Wheels Track Builder Unlimited Triple Loop Track Set	Versatile and customizable track set with three interconnected loops and adjustable ramps.	29.99	19.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
2165	\N	\N	Melissa & Doug Wooden Activity Table	Multi-activity wooden table with chalkboard, easel, building blocks, and storage.	79.99	59.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
2166	\N	\N	Play-Doh Kitchen Creations Ultimate Ice Cream Truck	Interactive playset with ice cream truck, dough, molds, and accessories.	29.99	19.99	Play-Doh	\N	\N	\N	Toys	\N	\N
2167	\N	\N	Pokémon Sword or Shield Video Game	Role-playing video game featuring Pokémon exploration, battles, and character customization.	59.99	49.99	Nintendo	\N	\N	\N	Toys	\N	\N
2168	\N	\N	Nerf Fortnite SP-L Elite Blaster	Fortnite-inspired Nerf blaster with pump-action, 10-dart clip, and dart storage.	19.99	14.99	Nerf	\N	\N	\N	Toys	\N	\N
2169	\N	\N	Squishmallows 16-Inch Kellytoy Plush	Super soft and huggable plush toy in a variety of animal characters.	19.99	14.99	Kellytoy	\N	\N	\N	Toys	\N	\N
2170	\N	\N	LOL Surprise! OMG House of Surprises	Spacious and interactive dollhouse with multiple rooms, furniture, and over 85 surprises.	149.99	109.99	LOL Surprise!	\N	\N	\N	Toys	\N	\N
2171	\N	\N	Minecraft Piglin Plush	Adorable and officially licensed Minecraft plush toy shaped like a Piglin.	14.99	9.99	Mojang	\N	\N	\N	Toys	\N	\N
2172	\N	\N	Funko Pop! Star Wars: The Child (Grogu)	Collectible vinyl figure based on the popular character from The Mandalorian series.	14.99	11.99	Funko	\N	\N	\N	Toys	\N	\N
2173	\N	\N	Roblox Adopt Me! Pet Trading Master Plush	Plush toy based on the popular Roblox game, featuring an exclusive pet code.	19.99	14.99	Roblox	\N	\N	\N	Toys	\N	\N
2174	\N	\N	Harry Potter Magical Minis Hogwarts Castle Playset	Detailed playset featuring the iconic Hogwarts castle with multiple rooms and characters.	149.99	109.99	Wizarding World	\N	\N	\N	Toys	\N	\N
2175	\N	\N	Among Us Crewmate Plush	Soft and cuddly plush toy based on the popular video game Among Us.	14.99	9.99	InnerSloth	\N	\N	\N	Toys	\N	\N
2176	\N	\N	Paw Patrol Lookout Tower	Interactive playset featuring the Paw Patrol lookout tower with elevator, vehicle launcher, and figurines.	79.99	59.99	Paw Patrol	\N	\N	\N	Toys	\N	\N
2177	\N	\N	Fortnite Victory Royale Series Legendary Skull Trooper Figure	Highly detailed and poseable action figure based on the popular Fortnite character.	19.99	14.99	Epic Games	\N	\N	\N	Toys	\N	\N
2178	\N	\N	Nintendo Switch Lite	Portable gaming console with a sleek design and access to a vast library of games.	199.99	179.99	Nintendo	\N	\N	\N	Toys	\N	\N
2179	\N	\N	Just Dance 2023 Video Game	Dance-based video game with a wide variety of popular songs and dance routines.	59.99	49.99	Ubisoft	\N	\N	\N	Toys	\N	\N
2180	\N	\N	VTech KidiZoom Creator Cam	Kid-friendly camera with a built-in microphone, video recorder, and editing features.	59.99	44.99	VTech	\N	\N	\N	Toys	\N	\N
2181	\N	\N	Barbie Career Doll and Playset	Barbie doll with a specific career and themed accessories.	19.99	14.99	Barbie	\N	\N	\N	Toys	\N	\N
2182	\N	\N	Hot Wheels Monster Trucks 5-Alarm	Massive and powerful Hot Wheels Monster Truck with oversized tires and unique design.	19.99	14.99	Hot Wheels	\N	\N	\N	Toys	\N	\N
2183	\N	\N	Melissa & Doug Wooden Magnetic Dress-Up Doll	Magnetic wooden doll with interchangeable clothing and accessories.	19.99	14.99	Melissa & Doug	\N	\N	\N	Toys	\N	\N
2184	\N	\N	Nerf Fortnite Heavy SR Blaster	Pump-action Nerf blaster inspired by the Fortnite video game, with high-capacity drum and dart storage.	29.99	24.99	Nerf	\N	\N	\N	Toys	\N	\N
2185	\N	\N	LEGO City Fire Station	Detailed LEGO model of a fire station with multiple floors, vehicles, and accessories.	99.99	79.99	LEGO	\N	\N	\N	Toys	\N	\N
2186	\N	\N	Play-Doh Kitchen Creations Ultimate Oven	Interactive playset with an oven, stovetop, utensils, and dough.	29.99	19.99	Play-Doh	\N	\N	\N	Toys	\N	\N
2187	\N	\N	Pokémon Trading Card Game Booster Box	Assortment of Pokémon trading cards with a variety of characters and rarities.	14.99	12.99	Pokémon	\N	\N	\N	Toys	\N	\N
2188	\N	\N	Squishmallows 20-Inch Avocado Plush	Super soft and adorable avocado-shaped Squishmallows plush toy.	29.99	24.99	Kellytoy	\N	\N	\N	Toys	\N	\N
2189	\N	\N	LOL Surprise! OMG Glamper	Spacious and feature-rich camper van with multiple rooms, furniture, and accessories.	199.99	149.99	LOL Surprise!	\N	\N	\N	Toys	\N	\N
2190	\N	\N	Harry Potter Hogwarts Express Train	Detailed model of the Hogwarts Express train with motorized engine and passenger cars.	149.99	109.99	Wizarding World	\N	\N	\N	Toys	\N	\N
2191	\N	\N	Minecraft Creeper Plush	Soft and cuddly plush toy shaped like the iconic Creeper from Minecraft.	19.99	14.99	Mojang	\N	\N	\N	Toys	\N	\N
2192	\N	\N	Roblox Welcome to Bloxburg Plush	Plush toy based on the popular Roblox game Bloxburg.	14.99	11.99	Roblox	\N	\N	\N	Toys	\N	\N
\.


--
-- Name: cymbal_products_uniq_id_seq1; Type: SEQUENCE SET; Schema: public; Owner: cymbal
--

SELECT pg_catalog.setval('public.cymbal_products_uniq_id_seq1', 2199, true);


--
-- Name: cymbal_embeddings cymbal_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cymbal_embeddings
    ADD CONSTRAINT cymbal_embeddings_pkey PRIMARY KEY (uniq_id);


--
-- Name: cymbal_products cymbal_products_pkey1; Type: CONSTRAINT; Schema: public; Owner: cymbal
--

ALTER TABLE ONLY public.cymbal_products
    ADD CONSTRAINT cymbal_products_pkey1 PRIMARY KEY (uniq_id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO cymbal;


--
-- PostgreSQL database dump complete
--

