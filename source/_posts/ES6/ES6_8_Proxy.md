# Proxy

## 1. 概述

ES6 原生提供 Proxy 构造函数，用来生成 Proxy 实例。

`var proxy = new Proxy(target, handler);`

**Proxy** 用于修改某些操作的默认行为，可以理解为在目标对象之前架设一层 “拦截” ，外界对该对象的访问，都必须先通过这层拦截，因此提供了一种机制，可以对外界的访问进行过滤和改写。可以译为 “代理器”

```jsx
var obj = new Proxy(
  {},
  {
    get: function (target, propKey, receiver) {
      console.log(`getting ${propKey}!`);
      return Reflect.get(target, propKey, receiver);
    },
    set: function (target, propKey, value, receiver) {
      console.log(`setting ${propKey}!`);
      return Reflect.set(target, propKey, value, receiver);
    },
  }
);

obj.count = 1;
//  setting count!
++obj.count;
//  getting count!
//  setting count!
//  2
```

一个技巧是将 Proxy 对象，设置到`object.proxy`属性，从而可以在`object`对象上调用。

```jsx
var object = { proxy: new Proxy(target, handler) };
```

Proxy 实例也可以作为其他对象的原型对象。

```jsx
var proxy = new Proxy(
  {},
  {
    get: function (target, propKey) {
      return 35;
    },
  }
);

let obj = Object.create(proxy);
obj.time; // 35

// proxy对象是obj对象的原型，obj对象本身并没有time属性，所以根据原型链，会在proxy对象上读取该属性，导致被拦截。
```

- **Proxy 支持的拦截操作如下**
  - **get(target, propKey, receiver)**：拦截对象属性的读取，比如`proxy.foo`和`proxy['foo']`。
  - **set(target, propKey, value, receiver)**：拦截对象属性的设置，比如`proxy.foo = v`或`proxy['foo'] = v`，返回一个布尔值。
  - **has(target, propKey)**：拦截`propKey in proxy`的操作，返回一个布尔值。
  - **deleteProperty(target, propKey)**：拦截`delete proxy[propKey]`的操作，返回一个布尔值。
  - **ownKeys(target)**：拦截`Object.getOwnPropertyNames(proxy)`、`Object.getOwnPropertySymbols(proxy)`、`Object.keys(proxy)`、`for...in`循环，返回一个数组。该方法返回目标对象所有自身的属性的属性名，而`Object.keys()`的返回结果仅包括目标对象自身的可遍历属性。
  - **getOwnPropertyDescriptor(target, propKey)**：拦截`Object.getOwnPropertyDescriptor(proxy, propKey)`，返回属性的描述对象。
  - **defineProperty(target, propKey, propDesc)**：拦截`Object.defineProperty(proxy, propKey, propDesc）`、`Object.defineProperties(proxy, propDescs)`，返回一个布尔值。
  - **preventExtensions(target)**：拦截`Object.preventExtensions(proxy)`，返回一个布尔值。
  - **getPrototypeOf(target)**：拦截`Object.getPrototypeOf(proxy)`，返回一个对象。
  - **isExtensible(target)**：拦截`Object.isExtensible(proxy)`，返回一个布尔值。
  - **setPrototypeOf(target, proto)**：拦截`Object.setPrototypeOf(proxy, proto)`，返回一个布尔值。如果目标对象是函数，那么还有两种额外操作可以拦截。
  - **apply(target, object, args)**：拦截 Proxy 实例作为函数调用的操作，比如`proxy(...args)`、`proxy.call(object, ...args)`、`proxy.apply(...)`。
  - **construct(target, args)**：拦截 Proxy 实例作为构造函数调用的操作，比如`new proxy(...args)`。

## 2. **Proxy 实例的方法**

### (1) get()

`get`方法用于拦截某个属性的读取操作，可以接受三个参数，依次为目标对象、属性名和 proxy 实例本身（严格地说，是操作行为所针对的对象），其中最后一个参数可选

`**get`方法可以继承。\*\*

```jsx
let proto = new Proxy(
  {},
  {
    get(target, propertyKey, receiver) {
      console.log("GET " + propertyKey);
      return target[propertyKey];
    },
  }
);

let obj = Object.create(proto);
obj.foo; // "GET foo"
```

**利用 Proxy，可以将读取属性的操作（get），转变为执行某个函数，从而实现属性的链式操作。**

```jsx
var pipe = function (value) {
  var funcStack = [];
  var oproxy = new Proxy(
    {},
    {
      get: function (pipeObject, fnName) {
        if (fnName === "get") {
          return funcStack.reduce(function (val, fn) {
            return fn(val);
          }, value);
        }
        funcStack.push(window[fnName]);
        return oproxy;
      },
    }
  );

  return oproxy;
};

var double = (n) => n * 2;
var pow = (n) => n * n;
var reverseInt = (n) => n.toString().split("").reverse().join("") | 0;

pipe(3).double.pow.reverseInt.get; // 63
```

**利用`get`拦截，实现一个生成各种 DOM 节点的通用函数`dom`。**

```jsx
const dom = new Proxy(
  {},
  {
    get(target, property) {
      return function (attrs = {}, ...children) {
        const el = document.createElement(property);
        for (let prop of Object.keys(attrs)) {
          el.setAttribute(prop, attrs[prop]);
        }
        for (let child of children) {
          if (typeof child === "string") {
            child = document.createTextNode(child);
          }
          el.appendChild(child);
        }
        return el;
      };
    },
  }
);

const el = dom.div(
  {},
  "Hello, my name is ",
  dom.a({ href: "//example.com" }, "Mark"),
  ". I like:",
  dom.ul(
    {},
    dom.li({}, "The web"),
    dom.li({}, "Food"),
    dom.li({}, "…actually that's it")
  )
);

document.body.appendChild(el);
```

**如果一个属性不可配置（configurable）且不可写（writable），则 Proxy 不能修改该属性，否则通过 Proxy 对象访问该属性会报错。**

```jsx
const target = Object.defineProperties(
  {},
  {
    foo: {
      value: 123,
      writable: false,
      configurable: false,
    },
  }
);

const handler = {
  get(target, propKey) {
    return "abc";
  },
};

const proxy = new Proxy(target, handler);

proxy.foo;
// TypeError: Invariant check failed
```

### (2) set()

`set`方法用来拦截某个属性的赋值操作，可以接受四个参数，依次为目标对象、属性名、属性值和 Proxy 实例本身，其中最后一个参数可选。

```jsx
const handler = {
  get(target, key) {
    invariant(key, "get");
    return target[key];
  },
  set(target, key, value) {
    invariant(key, "set");
    target[key] = value;
    return true;
  },
};
function invariant(key, action) {
  if (key[0] === "_") {
    throw new Error(`Invalid attempt to ${action} private "${key}" property`);
  }
}
const target = {};
const proxy = new Proxy(target, handler);
proxy._prop;
// Error: Invalid attempt to get private "_prop" property
proxy._prop = "c";
// Error: Invalid attempt to set private "_prop" property
```

### (3) apply()

`apply`方法拦截函数的调用、`call`和`apply`操作。

`apply`方法可以接受三个参数，分别是目标对象、目标对象的上下文对象（`this`）和目标对象的参数数组。

```jsx
var twice = {
  apply(target, ctx, args) {
    return Reflect.apply(...arguments) * 2;
  },
};
function sum(left, right) {
  return left + right;
}
var proxy = new Proxy(sum, twice);
proxy(1, 2); // 6
proxy.call(null, 5, 6); // 22
proxy.apply(null, [7, 8]); // 30
```

### (4) has()

`has()`方法用来拦截`HasProperty`操作，即判断对象是否具有某个属性时，这个方法会生效。典型的操作就是`in`运算符。

值得注意的是，`has()`方法拦截的是`HasProperty`操作，而不是`HasOwnProperty`操作，即`has()`
方法不判断一个属性是对象自身的属性，还是继承的属性。

对 `for...in` 不生效

### (5) **construct**()

`construct()`方法用于拦截`new`命令，下面是拦截对象的写法。

`construct()`方法可以接受三个参数。

- `target`：目标对象。
- `args`：构造函数的参数数组。
- `newTarget`：创造实例对象时，`new`命令作用的构造函数（下面例子的`p`）。

```jsx
const p = new Proxy(function () {}, {
  construct: function (target, args) {
    console.log("called: " + args.join(", "));
    return { value: args[0] * 10 };
  },
});

new p(1).value;
// "called: 1"
// 10
```

`construct()`方法返回的必须是一个对象，否则会报错。

它的目标对象必须是函数，否则就会报错。

### (6) **deleteProperty**()

`deleteProperty`方法用于拦截`delete`操作，如果这个方法抛出错误或者返回`false`，当前属性就无法被`delete`命令删除。

### (7) **defineProperty**()

`defineProperty()`方法拦截了`Object.defineProperty()`操作。

```jsx
var handler = {
  defineProperty(target, key, descriptor) {
    return false;
  },
};
var target = {};
var proxy = new Proxy(target, handler);
proxy.foo = "bar"; // 不会生效
```
