UPDATE `{PROJECT_ID}.{DATASET_ID}.stadium_logistics`
SET 
  details = 'Laptops, tablets, professional cameras, and large bags are strictly prohibited inside the stadium bowl for security reasons. There are no free secure lockers.',
  vector_content = 'Policy: Laptop, Tablet & Bag Policy. Details: Laptops, tablets, professional cameras, and large bags are strictly prohibited inside the stadium bowl for security reasons. There are no free secure lockers. Category: Device & Bag Policy'
WHERE id = 's_004';
