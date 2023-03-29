# Symbol

### 1. 概述

一种新的原始数据类型 `Symbol` ，表示独一无二的值。Symbol 值通过 `Symbol()`函数生成，也就是现在对象的属性名有两种类型，一种是字符串，一种是 Symbol 类型。

```jsx
let s = Symbol();

typeof s; // "symbol"
// 变量s就是一个独一无二的值
```

`Symbol()`函数可以接受一个字符串作为参数，表示对 Symbol 实例的描述。便于区分

```jsx
let s1 = Symbol("foo");
let s2 = Symbol("bar");

s1; // Symbol(foo)
s2; // Symbol(bar)

s1.toString(); // "Symbol(foo)"
s2.toString(); // "Symbol(bar)"

// 即使参数相同，两个值也不相同
let s1 = Symbol("foo");
let s2 = Symbol("foo");

s1 === s2; // false
```

<aside>
💡 Symbol 值可以显示的转为字符串 和布尔值，但是不能转数值

</aside>

### 2. **Symbol.prototype.description**

[ES2019](https://github.com/tc39/proposal-Symbol-description)提供了一个 Symbol 值的实例属性`description`，直接返回 Symbol 值的描述。

```jsx
const sym = Symbol("foo");

sym.description; // "foo"
```

### 3. **属性名的遍历**

Symbol 值作为属性名，遍历对象的时候，该属性不会出现在`for...in`、`for...of`循中，也不会被`Object.keys()`、`Object.getOwnPropertyNames()`、`JSON.stringify()`返回。

可以使用 `Object.getOwnPropertySymbols()`

```jsx
const obj = {};
let a = Symbol("a");
let b = Symbol("b");

obj[a] = "Hello";
obj[b] = "World";

const objectSymbols = Object.getOwnPropertySymbols(obj);

objectSymbols;
// [Symbol(a), Symbol(b)]
```

`Reflect.ownKeys()` 也可以

```jsx
let obj = {
  [Symbol("my_key")]: 1,
  enum: 2,
  nonEnum: 3,
};

Reflect.ownKeys(obj);
//  ["enum", "nonEnum", Symbol(my_key)]
```

### 4. **Symbol.for()，Symbol.keyFor()**

- `Symbol.for()`与`Symbol()`这两种写法，都会生成新的 Symbol。它们的区别是，前者会被登记在全局环境中供搜索，找到就会返回该值。后者不会，每次调用都会产生新值

```jsx
Symbol.for("bar") === Symbol.for("bar");
// true

Symbol("bar") === Symbol("bar");
```

- `Symbol.keyFor()`方法返回一个已登记的 Symbol 类型值的`key`

```jsx
let s1 = Symbol.for("foo");
Symbol.keyFor(s1); // "foo"

let s2 = Symbol("foo");
Symbol.keyFor(s2); // undefined
```

> `Symbol.for()`为 Symbol 值登记的名字，是全局环境的，不管有没有在全局环境运行。
