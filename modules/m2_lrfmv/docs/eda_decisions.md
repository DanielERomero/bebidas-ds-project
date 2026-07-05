# Decisiones EDA Bronze

## `registration_date` y antiguedad comercial

Se detectaron 340 clientes cuya primera compra ocurre antes de la fecha de registro del maestro de clientes. Esta inconsistencia sugiere que `registration_date` no debe interpretarse como inicio real de relacion comercial transaccional.

Para evitar sesgo en LRFMV, el modulo calculara `length_days` usando `first_purchase_date` derivada de `transactions_raw`. La variable `registration_date` se mantiene en Bronze como atributo crudo del maestro, pero no sera usada para el calculo de antiguedad comercial.
