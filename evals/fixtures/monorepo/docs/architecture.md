# Architecture notes

Services talk to each other only through `shared/`. Billing is the only
service that keeps a lifecycle; the others are stateless transformations.
