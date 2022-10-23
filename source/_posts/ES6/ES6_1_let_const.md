---
title: ES6 学习笔记（1） - let 和 const
date: 2022-05-28 22:31:46
updated:
tags:
  - ES6
  - es6
categories: ES6
keywords: "解构赋值,解构"
description:
top_img:
comments:
cover:
toc:
toc_number:
toc_style_simple:
copyright:
copyright_author:
copyright_author_href:
copyright_url:
copyright_info:
mathjax:
katex:
aplayer:
highlight_shrink:
aside:
---

### 1. let

- **基本用法**

`let` 为 ES6 新增命令，用于声明变量。用法类似 `var` 但是所声明的变量，只有在 `let` 命令所在的代码块内有效。

```jsx
{
  let a = 10;
  var b = 1;
}
console.log(a); // // ReferenceError: a is not defined.
console.log(b); // 1
```

`for` 循环的计数器里`let`和`var`有着不一样的表现

```jsx
for (var i = 0; i < 10; i++) {
  setTimeout(function () {
    console.log(i); // 执行此代码时，同步代码for循环已经执行完成
  }, 0);
}
// 输出结果
// 10   共10个

for (let i = 0; i < 10; i++) {
  setTimeout(function () {
    console.log(i); //  i 是循环体内局部作用域，不受外界影响。
  }, 0);
}
// 输出结果：
// 0  1  2  3  4  5  6  7  8 9
```

以上的案例有一个需要注意的点： 变量 `i` 如果是 `var` 声明的，在全局范围内都有效，每次循环，变量 `i` 的值都会发生改变，但是循环体内的 `i` 指向的就是全局的 `i` 。而用 `let` 声明的 i 在每次循环时都会重新创建变量，

- **let 不存在变量提升**

`let` 不会像 `var` 一样会发上“变量提升”，即变量可以在声明之前使用，值为`undefined` 。

```jsx
// var
console.log(a); // undefined
var a = 10;

// let
console.log(b); // 报错 ReferenceError
let b = 20;
```

- **暂时性死区(temporal dead zone, TDZ)**

暂时性死区是指，只要块级作用域内存在 `let` 声明，它所在的变量就 binding 这个区域了，不再受外部的影响。总结为：在代码块内，使用`let`声明变量前，该变量都不可用的。

```jsx
var tmp = 123;
if(true){
	tmp = 'abc', // ReferenceError
	let tmp // let声明tmp导致其绑定了这个块级作用域
}
```

- **不允许重复声明**

`let` 不允许在相同作用域内，重复声明一个变量。

```jsx
function func() {
  let a = 10;
  var a = 1;
}
func(); // 报错

function func(arg) {
  let arg;
}
func(); // 报错

function func(arg) {
  {
    let arg;
  }
}
func(); // 不报错
```

### 2. 块级作用域

- **没有块级作用与的坏处：**

```jsx
// 1. 内层变量可能会覆盖外层变量
var tmp = new Date();

function fn() {
  console.log(tmp);
  if (false) {
    var tmp = "hello world";
  }
}

fn(); // undefined 原因在于变量提升，导致内层的 tmp 变量覆盖了外层的tmp变量

// 2. 用来计数的循环变量泄露为全局变量
var s = "hello";

for (var i = 0; i < s.length; i++) {
  console.log(s[i]);
}

console.log(i); // 5
```

- **块级作用域与函数声明**

ES5 规定，函数只能在顶层作用域和函数作用域之中声明，不能在块级作用域声明。一下两种情况在 ES5 中都是非法的，但是浏览器没有遵守这个规定，所以在浏览器中依然可以运行

```jsx
// 情况一
if (true) {
  function f() {}
}

// 情况二
try {
  function f() {}
} catch (e) {
  // ...
}
```

ES6 引入了块级作用域，明确允许在块级作用域中声明函数，函数声明语句行为类似于`let`

```jsx
function f() {
  console.log("I am outside!");
}

(function () {
  if (false) {
    // 重复声明一次函数f
    function f() {
      console.log("I am inside!");
    }
  }

  f();
})();

// ES5 环境
function f() {
  console.log("I am outside!");
}

(function () {
  function f() {
    console.log("I am inside!");
  }
  if (false) {
  }
  f();
})();

// 浏览器行为：
// - 允许在块级作用域内声明函数。
// - 函数声明类似于var，即会提升到全局作用域或函数作用域的头部。
// - 同时，函数声明还会提升到所在的块级作用域的头部。

// 浏览器的 ES6 环境
function f() {
  console.log("I am outside!");
}
(function () {
  var f = undefined;
  if (false) {
    function f() {
      console.log("I am inside!");
    }
  }

  f();
})();
// Uncaught TypeError: f is not a function
```

所以：应该避免在块级作用域内声明函数。如果确实需要，应该写成函数表达式

### 3. const

- **基本用法**

  `const` 声明一个只读常量。一旦声明，值就不能改变，且声明时就必须立即初始化

  `const` 作用域与`let` 相同：只在声明所在的作用域内有效

  `const` 命令声明的常量也是不提升，同样存在暂时性死区，只能在声明的位置后面使用。

  `const` 声明的常量，也与 let 一样不可重复声明。

注意 ⚠️：`const`实际上保证的，并不是变量的值不得改动，而是变量指向的那个内存地址所保存的数据不得改动。
