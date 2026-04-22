from agent2.parsing.code_parsers.parse_csharp import parse_csharp_elements

def dump(elements, indent=0):
    for el in elements:
        pad = "    " * indent
        print(f"{pad}{el.identifier:40} line={el.line_start:>3} header={el.header!r}")
        if el.description:
            first = el.description.splitlines()[0]
            print(f"{pad}    docstring: {first!r}")
        dump(el.elements, indent + 1)

script_cs_1 = r'''
using System;
using System.Collections.Generic;

// A top-level comment

///<summary>
/// This is a sample namespace
///</summary>
namespace MyApp
{
    //<summary>Doc for Outer</summary>
    public class Outer<T> : Base
    {
        // A field
        public int X = 0;

        ///<summary>Doc for Inner</summary>
        private class Inner
        {
            public void InnerMethod()
            {
                // method body

                void LocalFunction()
                {
                    // local function
                }

                LocalFunction();
            }
        }

        [Obsolete]
        public void MethodWithAttribute()
        {
        }
    }

    public struct MyStruct
    {
    }

} // end namespace

// C#9 top-level function
void TopLevelFunction(int x)
{
    Console.WriteLine(x);
}
'''

script_cs_2 = r'''
/// <summary>Module doc comment</summary>
using System;

delegate void MyDelegate(string s);

enum Colors
{
    Red,
    Green,
    Blue
}

interface IMyInterface
{
    void DoWork();
}

class A
{
    class B
    {
        class C
        {
            void M1()
            {
                void Inner()
                {
                }
                Inner();
            }
        }
    }

    public static A Create()
    {
        return new A();
    }

    public void InstanceMethod()
    {
        int x = 10;

        /// <summary>Local function doc</summary>
        void Local()
        {
        }

        Local();
    }
}

// Top-level statements
int y = 5;
Console.WriteLine(y);
'''

print("========= CSHARP SCRIPT 1 =========\n")
elements1 = parse_csharp_elements(script_cs_1)
dump(elements1)

print("\n========= CSHARP SCRIPT 2 =========\n")
elements2 = parse_csharp_elements(script_cs_2)
dump(elements2)
