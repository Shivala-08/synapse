# JavaScript Fundamentals — 15 Q&A Pairs

**Q1. Does JavaScript have separate `int`, `float`, and `double` types like C/C++/Java? What does it use instead?**
A: No. JavaScript uses one single number type for integers, decimals, and negative numbers alike — there's no separate int/float/double.

**Q2. What is the output of `console.log(10 + 2 * 5);` and `console.log((10 + 2) * 5);`? Why do they differ?**
A: `20` and `60`. JavaScript follows BODMAS — multiplication runs before addition in the first line, while brackets force the addition to happen first in the second.

**Q3. Template literals (backticks) let you "inject" expressions with `${}`. Does this work with single or double quotes too?**
A: No — `${}` expression injection works ONLY with backticks (template strings), not with single or double quotes.

**Q4. What does `typeof null` return, and why is this called out as a "JS bug"?**
A: It returns `"object"`, even though `null` represents an intentional empty value, not an object. It's a long-standing quirk in JavaScript that's worth remembering for exams.

**Q5. What's the difference between `undefined` and `null`?**
A: `undefined` means a variable was declared but never assigned a value (JS sets this automatically). `null` is an *intentional* empty value that a programmer explicitly assigns.

**Q6. Why is `var` discouraged in modern JavaScript in favor of `let` and `const`?**
A: The notes flag `var` as "old, avoid" — `let` and `const` are the modern, preferred way to declare variables (`let` for reassignable values, `const` for constants that can't be reassigned).

**Q7. What happens if you try to reassign a `const` variable, e.g. `const PI = 3.14; PI = 4;`?**
A: It throws an error — `const` variables cannot be reassigned after declaration.

**Q8. In a `switch` statement, what happens if you forget the `break` keyword inside a `case`?**
A: Execution "falls through" into the next case instead of stopping — `break` is what prevents fall-through.

**Q9. Why is `for...in` NOT recommended for looping over arrays, even though it works?**
A: It iterates over indexes as strings (not values), can also pick up extra properties added to the array, and doesn't guarantee order in edge cases. Use `for` or `for...of` instead — `for...in` is meant for objects.

**Q10. Given `function demo(a = 10, b) { console.log(a, b); }`, what does `demo(5)` print, and is this valid even though `a` (with a default) comes before `b` (without one)?**
A: It prints `5 undefined`. It's valid JavaScript — unlike Python, JS allows default parameters in any position — but it's flagged as bad practice; defaults should go last for clarity (e.g. `greet(name, age = 18)`).

**Q11. When exactly does a JavaScript default parameter get used?**
A: Only when the argument passed is `undefined` — not for any other falsy value like `0`, `""`, or `null`.

**Q12. Does `arr.slice(1, 3)` modify the original array? Does `arr.splice(1, 2)`? What does each return?**
A: `slice()` does NOT modify the original array — it returns a copied portion. `splice()` DOES modify the original array (it's destructive) and returns an array of the removed elements.

**Q13. Given `let arr = [1, 2, 5]; arr.splice(2, 0, 3, 4);`, what is `arr` afterward, and what do the four arguments mean?**
A: `arr` becomes `[1, 2, 3, 4, 5]`. The arguments are: start at index `2`, delete `0` elements, then insert `3` and `4` at that position.

**Q14. How do you access a property of an object two different ways, e.g. the `age` property of `student`?**
A: `student.age` (dot notation) or `student["age"]` (bracket notation).

**Q15. What does `delete student.marks;` do, and how do you loop over all of an object's key-value pairs?**
A: `delete` removes the `marks` property from the `student` object entirely. To loop over all keys and values, use `for (let key in student) { console.log(key, student[key]); }`.
