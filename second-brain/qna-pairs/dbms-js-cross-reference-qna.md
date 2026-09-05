# Cross-Referencing Q&A — DBMS/SQL × JavaScript (15 Pairs)

These test whether you can connect the same underlying idea across both subjects — a common trick in mixed exams and vivas.

**Q1. Both SQL and JavaScript have a "missing value" concept — SQL's NULL and JS's `undefined`/`null`. Compare `WHERE email = NULL` in SQL with `if (x == null)` in JS — is either comparison safe?**
A: Neither is fully safe by default. In SQL, `= NULL` always returns nothing because NULL means "unknown" and isn't equal to anything — you must use `IS NULL`. In JS, `x == null` (loose equality) actually IS the accepted safe idiom because it matches both `null` and `undefined` — but `x === null` only matches `null`, not `undefined`. The lesson in both languages: know exactly what your equality check does with "empty."

**Q2. SQL's `UNIQUE` constraint permits multiple NULLs in a column. JavaScript's `Set` object also handles duplicates — does a JS `Set` treat multiple `undefined` or `NaN` values the same way SQL treats multiple NULLs?**
A: No — they behave oppositely. SQL's UNIQUE constraint does NOT block duplicate NULLs (each NULL is "unknown," so no two are considered equal to each other). A JS `Set` DOES dedupe `undefined` and `NaN` — adding `undefined` twice, or `NaN` twice, only keeps one instance, because `Set` uses SameValueZero equality, not `IS NULL`-style logic.

**Q3. In SQL, `TRUNCATE` and `DROP` auto-commit and can't be rolled back, while `DELETE` can be. In JavaScript, is there an equivalent "undo" mechanism when you mutate an array with `splice()`?**
A: No — JavaScript has no built-in rollback. `splice()` permanently mutates the array in place, same as how `TRUNCATE`/`DROP` are irreversible in SQL. If you need an "undo," you must manually keep a copy first (the JS equivalent of using `slice()` to snapshot before mutating) — there's no COMMIT/ROLLBACK safety net like SQL's TCL.

**Q4. `splice()` in JS modifies the original array (destructive); `slice()` doesn't (non-destructive). Which pair of SQL commands maps onto this same "modifies vs. doesn't modify" distinction — SELECT/UPDATE, or DELETE/TRUNCATE?**
A: SELECT vs UPDATE. `SELECT` only reads data and changes nothing (like `slice()`), while `UPDATE` modifies existing rows in place (like `splice()`). `DELETE`/`TRUNCATE` both remove data, so that pair doesn't capture the modifies-vs-reads distinction the same way.

**Q5. SQL's `WHERE` clause filters which rows an `UPDATE` or `DELETE` affects. What's the closest JavaScript equivalent when you want to update only some elements of an array, not all of them?**
A: An `if` condition inside a loop (or `.filter()`/`.map()` with a condition) — e.g. looping through an array and only changing elements that satisfy a check, the same way `WHERE` scopes an `UPDATE` to matching rows. Forgetting the condition in either language has the same failure mode: SQL updates every row, JS updates/loops over every element.

**Q6. SQL enforces a column's `CHECK` constraint (e.g. `CHECK (age >= 18)`) at insert time, rejecting bad data before it's stored. Does JavaScript have anything built into the language that enforces a similar rule automatically when you assign a variable?**
A: No. JavaScript has no automatic validation on assignment — `let age = -5;` is accepted without complaint. Any equivalent check (like an `if` statement or a function that validates before accepting a value) has to be written manually; SQL's CHECK constraint is enforced by the database itself.

**Q7. A SQL `FOREIGN KEY` prevents an `orders` row from referencing a `customer_id` that doesn't exist (no orphan records). What happens in JavaScript if you access `student.address.city` but `address` was never defined on that object?**
A: It throws a runtime error ("Cannot read properties of undefined"), because JS doesn't stop you from creating the reference in the first place — there's no constraint layer checking beforehand. SQL blocks the bad reference at write time; JS only fails later, when you try to use it (which is why nested-object access is a common source of bugs — the notes' `user.address.city` example only works because `address` was actually defined).

**Q8. Compare a SQL schema's `PRIMARY KEY` (must be unique, not null, one per table) with a JavaScript object's property names (keys). Can a JS object have two properties with the exact same key?**
A: No — the same key in an object literal simply overwrites the earlier value, similar in spirit to how a PRIMARY KEY can't have duplicates. But the mechanism differs: SQL actively *rejects* a duplicate primary key with an error, while JS silently keeps only the last-assigned value for a repeated key, with no error at all.

**Q9. SQL's DDL commands (`CREATE`, `ALTER`, `DROP`) build/reshape a table's *structure*, while DML (`INSERT`, `UPDATE`) changes the *data* inside it. Which JavaScript concepts map onto "structure" vs "data" for an object?**
A: Defining the object's shape (declaring `let student = {name: ..., age: ...}` — deciding which properties exist) is closest to DDL/structure. Later changing values with `student.age = 19;` (UPDATE-like) or adding a new property with `student.newProp = x;`, or removing one with `delete student.marks;` (DROP COLUMN-like), is the DML/data-manipulation side.

**Q10. SQL's `INSERT INTO students VALUES (...)` without naming columns requires values in the exact defined column order. Does JavaScript's array destructuring (or plain positional arguments) rely on the same "position matters" rule?**
A: Yes — positional function arguments in JS (e.g. `greet("Palak", 18)` matching `function greet(name, age)`) work the same way: order determines which value maps to which parameter, just like unlabelled SQL INSERT values map by column position. Both are risky for the same reason: reorder the underlying definition (table columns / function parameters) and every positional call silently breaks or misassigns.

**Q11. In SQL, `AND` and `OR` combine conditions in a `WHERE` clause. JavaScript has the same `&&` and `||` operators — but the notes warn about a specific UPDATE mistake using AND. What was it, and does the same category of mistake exist in JS?**
A: The SQL mistake: writing `SET city = 'Pune' AND is_prime = TRUE` uses `AND` where a comma was needed — SQL reads it as one boolean expression instead of two assignments, silently storing a wrong value. JavaScript doesn't have this exact trap (assignments are separated by semicolons or commas in a very different syntax), but the underlying lesson is the same in both: confusing an "assignment" operation with a "logical condition" operation produces silently wrong results rather than an obvious error.

**Q12. SQL's `TCL` (COMMIT/ROLLBACK) exists because multi-step operations (like a bank transfer) need "all steps or none." Does a JavaScript `for` loop offer any equivalent guarantee if it errors out halfway through modifying an array?**
A: No — JavaScript offers no such guarantee. If a `for` loop throws an error on iteration 3 of 5, the first two iterations' effects on the array stay exactly as they were left; there's no automatic rollback. This is the opposite of SQL's transaction guarantee, and is why "all-or-nothing" logic in JS has to be hand-built (e.g. working on a copy and only committing it back if every step succeeds).

**Q13. Compare `typeof` in JavaScript with a SQL column's declared datatype (`INT`, `VARCHAR`, etc.). Is `typeof` checked at the same time as a SQL datatype constraint?**
A: No — SQL datatypes are enforced at write time (the database rejects an INSERT that doesn't match the column type). `typeof` in JS is just a runtime inspection tool — it tells you what type a value currently is, but nothing stops you from assigning a completely different type to the same variable later (`let x = 10; x = "hello";` is perfectly legal), unlike a SQL column, which is locked to one datatype for its lifetime.

**Q14. SQL distinguishes structured, semi-structured, and unstructured data — with JSON documents being the classic semi-structured example. Where in the JavaScript notes does an object literal resemble that same JSON-style semi-structured shape?**
A: The `student` object example (`{name: "Palak", age: 18, marks: 90, greet: function(){...}}`) — like a semi-structured JSON document, it has some structure (each property has a name) but no rigid schema forcing every "student" object to have identical fields, unlike a SQL table row where every column is fixed for every record.

**Q15. Both notes cover a "removal" operation: SQL has DELETE/TRUNCATE/DROP with three different scopes, and JS array methods include `pop()`, `shift()`, and `splice()`. Match `pop()` and `shift()` to the SQL operation they most resemble in *scope* (not permanence).**
A: Both `pop()` (removes the last element) and `shift()` (removes the first element) resemble `DELETE` in scope — they remove specific, targeted entries rather than everything (like `TRUNCATE`) or destroying the whole structure (like `DROP`). None of the three JS methods destroy the array itself, so none maps onto DROP.
