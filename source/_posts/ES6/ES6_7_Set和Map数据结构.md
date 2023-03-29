# Set 和 Map 数据结构

## Set

## 1. Set

`Set`本身是一个构造函数，用来生成 Set 数据结构。它类似于数组，但是成员的值都是唯一的，没有重复的值。

```jsx
const s = new Set();

[2, 3, 5, 4, 5, 2, 2].forEach(x => s.add(x));

for (let i of s) {
  console.log(i);
}

// 等同于
 const s = new Set([2, 3, 5, 4, 5, 2, 2])

// 去除数组的重复成员
[...new Set(array)]
```

`Set`函数可以接受一个数组（或者具有 iterable 接口的其他数据结构）作为参数，用来初始化。

## 2. Set **实例的属性和方法**

Set 结构的实例有以下属性。

- `Set.prototype.constructor`：构造函数，默认就是`Set`函数。
- `Set.prototype.size`：返回`Set`实例的成员总数。

Set 实例的方法分为两大类：操作方法（用于操作数据）和遍历方法（用于遍历成员）。下面先介绍四个操作方法。

- `Set.prototype.add(value)`：添加某个值，返回 Set 结构本身。
- `Set.prototype.delete(value)`：删除某个值，返回一个布尔值，表示删除是否成功。
- `Set.prototype.has(value)`：返回一个布尔值，表示该值是否为`Set`的成员。
- `Set.prototype.clear()`：清除所有成员，没有返回值。

Set 结构的实例有四个遍历方法，可以用于遍历成员。

- `Set.prototype.keys()`：返回键名的遍历器
- `Set.prototype.values()`：返回键值的遍历器
- `Set.prototype.entries()`：返回键值对的遍历器
- `Set.prototype.forEach()`：使用回调函数遍历每个成员

## Map

## 1. Map

`Map`是类似于对象的一种键值对集合，但是 ‘键’ 可以是任意类型的值（包括对象）

```jsx
const m = new Map();
const o = { p: "Hello World" };

m.set(o, "content");
m.get(o); // "content"

m.has(o); // true
m.delete(o); // true
m.has(o); // false
```

`Map` 构造函数接受数组作为参数，相当于下面算法

```jsx
const items = [
  ["name", "张三"],
  ["title", "Author"],
];

const map = new Map();

items.forEach(([key, value]) => map.set(key, value));
```

不仅仅是数组，任何具有 Iterator 接口、且每个成员都是一个双元素的数组的数据结构都可以当作`Map`构造函数的参数。

```jsx
const set = new Set([
  ["foo", 1],
  ["bar", 2],
]);
const m1 = new Map(set);
m1.get("foo"); // 1

const m2 = new Map([["baz", 3]]);
const m3 = new Map(m2);
m3.get("baz"); // 3
```

## 2. Map 的实例属性和操作方法

- **`size` 属性**
  `size`属性返回 Map 结构的成员总数

  ```jsx
  const map = new Map();
  map.set("foo", true);
  map.set("bar", false);

  map.size; //
  ```

- **Map.prototype.set(key, value)**
  `set`方法设置键名`key`对应的键值为`value`，然后返回整个 Map 结构。如果`key`已经有值，则键值会被更新，否则就新生成该键

  ```jsx
  const m = new Map();

  m.set("edition", 6); // 键是字符串
  m.set(262, "standard"); // 键是数值
  m.set(undefined, "nah"); // 键是 undefined

  // set 方法返回Map结构，因此可以采用链式写法
  m.set(1, "a").set(2, "b");
  ```

- **Map.prototype.get(key)**
  `get`方法读取`key`对应的键值，如果找不到`key`，返回`undefined`。
- **Map.prototype.has(key)**
  `has`方法返回一个布尔值，表示某个键是否在当前 Map 对象之中。
- Map.prototype.delete(key)
  `delete`方法删除某个键，返回`true`。如果删除失败，返回`false`。
- Map.prototype.clear(key)
  `clear`方法清除所有成员，没有返回值。

### 遍历方法

Map 结构原生提供三个遍历器生成函数和一个遍历方法。

- `Map.prototype.keys()`：返回键名的遍历器。
- `Map.prototype.values()`：返回键值的遍历器。
- `Map.prototype.entries()`：返回所有成员的遍历器。
- `Map.prototype.forEach()`：遍历 Map 的所有成员。

```jsx
// Map 也可使用扩展运算符(...)
const map = new Map([
  [1, 'one'],
  [2, 'two'],
  [3, 'three'],
]);

[...map.keys()]
// [1, 2, 3]

[...map.values()]
// ['one', 'two', 'three']

[...map.entries()]
// [[1,'one'], [2, 'two'], [3, 'three']]

[...map]
// [[1,'one'], [2, 'two'], [3, 'three']]
```
