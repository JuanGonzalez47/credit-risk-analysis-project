--application_train.csv  
--application_test.csv  
--bureau.csv  
--bureau_balance.csv  
--credit_card_balance.csv  
--installments_payments.csv  
--POS_CASH_balance.csv  
--previous_application.csv 

-- Abre una nueva consola en la ruta del proyecto:

--Copiar

/*mysql -u root -p --local-infile=1
SET GLOBAL local_infile = 1;
SHOW VARIABLES LIKE 'local_infile';
Debe mostrar: ON */

USE bronze;
LOAD DATA LOCAL INFILE '/archivos.csv'
INTO TABLE previous_application
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
