-- ============================================================================
-- PetVerse Sanctuary Analytics - Populate Cloud Storage ObjectRef Columns
-- ============================================================================
-- Placeholders:
--   __PROJECT_ID__ -> Your Google Cloud project ID
--   __REGION__     -> Your BigQuery dataset region (e.g., __REGION__)
-- ============================================================================

SET @@location = '__REGION__';

ALTER TABLE `__PROJECT_ID__.petverse.pets`
ADD COLUMN IF NOT EXISTS profile_picture STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>,
ADD COLUMN IF NOT EXISTS additional_media ARRAY<STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>>;

-- Backfill showcase rows (Id 1..3) if not already populated interactively
UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/yoda_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Yoda_asks_for_cuddles.mp4', '__REGION__.pet-connection')))]
WHERE Id = 1 AND profile_picture IS NULL;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/madonna_profile_picture.jpg', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Madonna_description.wav', '__REGION__.pet-connection')))]
WHERE Id = 2 AND profile_picture IS NULL;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/pixel_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pixel_thug_life.mp4', '__REGION__.pet-connection'))),
                        (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pixel_description.wav', '__REGION__.pet-connection')))]
WHERE Id = 3 AND profile_picture IS NULL;

-- Populate remaining sanctuary residents (Id 4..14)
UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/sql_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/SQL_description.wav', '__REGION__.pet-connection'))),
                        (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/SQL_favorite_toy.mp4', '__REGION__.pet-connection')))]
WHERE Id = 4;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/buddy_golden_retriever.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 5;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/daisy_french_bulldog.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 6;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/max_german_shepherd.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/max_description_tells_jokes.mp4', '__REGION__.pet-connection')))]
WHERE Id = 7;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = NULL,
    additional_media = NULL
WHERE Id = 8;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = NULL,
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/rocky_description.mp4', '__REGION__.pet-connection')))]
WHERE Id = 9;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/pip_hamster.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pip_Hamster_Wheel_Video_Generated.mp4', '__REGION__.pet-connection')))]
WHERE Id = 10;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = NULL,
    additional_media = NULL
WHERE Id = 11;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/scales_snake.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 12;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = NULL,
    additional_media = NULL
WHERE Id = 13;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/Joel_Profile_Picture.jpg', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Catwalk.jpg', '__REGION__.pet-connection'))),
                        (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Flowers.jpg', '__REGION__.pet-connection'))),
                        (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Plays.jpg', '__REGION__.pet-connection')))]
WHERE Id = 14;
