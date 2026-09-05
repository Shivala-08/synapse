# DBMS & SQL — 15 Q&A Pairs

**Q1. Why does an application "feel intelligent" according to the course's core idea?**
A: Because it stored observations first — intelligent-seeming features (recommendations, top picks) are just analysis run on data that was collected and stored earlier. Store first, analyse later.

**Q2. A university stores each student's documents with different fields per student (some have internships, some have certifications), but every student still has a name and enrollment ID. What category of data is this, and why?**
A: Semi-structured — some organizational properties exist (name, enrollment ID) but there's no rigid shared schema, so content varies per record. Analogy: the university locker.

**Q3. A table has 3 rows and only one of them needs a new attribute (loyalty_points). Compare what happens in a relational table vs. a JSON document store.**
A: Relational: a new column is added for all rows, and the rows that don't have the value get NULL — wasted storage plus a schema migration. JSON: only the one document that has the new field changes; the others stay untouched.

**Q4. Two staff members open the same spreadsheet and both edit row 42 at the same time. What problem does this illustrate, and how does a DBMS solve it?**
A: Concurrent access control — in a file, the last save silently overwrites the other's changes. A DBMS locks the specific row being edited so others can still access other rows, and detects/resolves conflicts automatically.

**Q5. What is an orphan record, and which constraint prevents it?**
A: A record that references a parent row that no longer exists (e.g., an order pointing to a deleted customer). The FOREIGN KEY constraint prevents it by blocking inserts/deletes that would create one.

**Q6. Map these real-world concepts to their database equivalents: Entity, Attribute, Instance, Relationship.**
A: Entity → Table, Attribute → Column, Instance → Row, Relationship → shared value (foreign key).

**Q7. A column is declared UNIQUE but not NOT NULL. Can it contain more than one NULL value? Explain.**
A: Yes. UNIQUE only forbids duplicate non-NULL values; it does not forbid NULLs. NOT NULL is the separate constraint that blocks empty values. The two are independent.

**Q8. What's the difference between a superkey, a candidate key, and a primary key?**
A: A superkey is any column set that uniquely identifies a row (may include extra columns). A candidate key is a *minimal* superkey — remove any column and it stops being unique. The primary key is the one candidate key chosen as the table's main identifier; every primary key is a candidate key, and every candidate key is a superkey, but not the reverse.

**Q9. Why does a many-to-many relationship (e.g., Students ↔ Courses) require a third table instead of a foreign key on either side?**
A: A relational table cell can't hold a list of values, so neither Students nor Courses can store multiple links directly. A junction table (e.g., Enrollment) holds a foreign key to each side, with a composite primary key of both IDs.

**Q10. Which SQL command category does each belong to: CREATE, INSERT, COMMIT, GRANT?**
A: CREATE → DDL (Data Definition Language), INSERT → DML (Data Manipulation Language), COMMIT → TCL (Transaction Control Language), GRANT → DCL (Data Control Language).

**Q11. Why can a foreign key constraint fail when creating the `orders` table before the `customers` table?**
A: A foreign key must reference a table that already exists — `orders.cust_id` can't point to `customers.cust_id` if `customers` hasn't been created yet. Parent tables must be created before child tables that reference them.

**Q12. Compare DELETE, TRUNCATE, and DROP on: what they remove, whether WHERE is allowed, and whether they can be rolled back.**
A: DELETE removes selected rows (WHERE allowed, DML, rollback possible before COMMIT). TRUNCATE removes all rows but keeps the table structure (no WHERE, DDL, cannot be rolled back). DROP removes the entire table — structure and data (no WHERE, DDL, cannot be rolled back).

**Q13. Why is `WHERE email = NULL` always wrong, and what should be used instead?**
A: NULL means "unknown" — it isn't equal to anything, including another NULL, so `= NULL` never matches any row. Use `IS NULL` (or `IS NOT NULL`) instead.

**Q14. In `UPDATE customers SET city = 'Pune' AND is_prime = TRUE WHERE cust_id = 105;`, what's wrong with using AND here, and what should replace it?**
A: AND treats the SET clause as one boolean expression instead of two separate assignments, producing a wrong stored value. Assignments in SET must be separated by commas: `SET city = 'Pune', is_prime = TRUE`.

**Q15. In a fund transfer (debit A, credit B), the system crashes right after debiting A but before crediting B. What database feature prevents money from vanishing, and what do COMMIT and ROLLBACK do within it?**
A: A transaction — it guarantees all steps complete or none do. COMMIT makes every change since the transaction began permanent and visible to others; ROLLBACK reverses all changes since the transaction began, but only works before COMMIT has run.
