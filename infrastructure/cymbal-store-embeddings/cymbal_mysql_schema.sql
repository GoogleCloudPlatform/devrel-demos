/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.11-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: 34.132.177.226    Database: quickstart_db
-- ------------------------------------------------------
-- Server version	8.4.4-google

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cymbal_embedding`
--

DROP TABLE IF EXISTS `cymbal_embedding`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cymbal_embedding` (
  `uniq_id` varchar(100) NOT NULL,
  `description` text,
  `embedding` varbinary(3072) DEFAULT NULL COMMENT 'GCP MySQL Vector Column V1, dimension=768',
  PRIMARY KEY (`uniq_id`),
  CONSTRAINT `vector_dimensions_chk_1743437002911643000` CHECK (((`embedding` is null) or (length(`embedding`) <=> 3072)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cymbal_inventory`
--

DROP TABLE IF EXISTS `cymbal_inventory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cymbal_inventory` (
  `store_id` int NOT NULL,
  `uniq_id` text NOT NULL,
  `inventory` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cymbal_products`
--

DROP TABLE IF EXISTS `cymbal_products`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cymbal_products` (
  `uniq_id` varchar(100) NOT NULL,
  `crawl_timestamp` datetime DEFAULT NULL,
  `product_url` text,
  `product_name` text,
  `product_description` text,
  `list_price` decimal(10,2) DEFAULT NULL,
  `sale_price` decimal(10,2) DEFAULT NULL,
  `brand` text,
  `item_number` text,
  `gtin` text,
  `package_size` text,
  `category` text,
  `postal_code` text,
  `available` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`uniq_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cymbal_stores`
--

DROP TABLE IF EXISTS `cymbal_stores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cymbal_stores` (
  `store_id` int NOT NULL,
  `name` text,
  `url` text,
  `street_address` text,
  `city` text,
  `state` varchar(3) DEFAULT NULL,
  `zip_code` int DEFAULT NULL,
  `country` varchar(3) DEFAULT NULL,
  `phone_number_1` text,
  `phone_number_2` text,
  `fax_1` text,
  `fax_2` text,
  `email_1` text,
  `email_2` text,
  `website` text,
  `open_hours` text,
  `latitude` text,
  `longitude` text,
  `facebook` text,
  `twitter` text,
  `instagram` text,
  `pinterest` text,
  `youtube` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-04-04 19:02:07
