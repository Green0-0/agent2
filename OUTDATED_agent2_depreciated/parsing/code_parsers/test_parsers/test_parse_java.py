from agent2.parsing.code_parsers.parse_java import parse_java_elements

script_1 = r'''
package com.example;

/** 
 * Module‐level Javadoc
 */
import java.util.List;
import static java.lang.System.out;

@CustomAnnotation
public class Outer {
    /**
     * Doc for Outer class
     */
    static {
        // static initializer
        init();
    }

    private int field; // not a method

    /** Inner interface */
    public interface InnerInterface {
        void perform();
    }

    @Deprecated
    public void outerMethod(String param) throws Exception {
        // some logic
        class LocalClass {
            void localMethod() {}
        }
        LocalClass lc = new LocalClass();
    }

    /** Factory method */
    @MyFactory
    public static Outer create() {
        return new Outer();
    }

    record InnerRecord(int x, String y) {
        /** Record method doc */
        public int recordMethod() { return x; }
    }
}
'''

script_2 = r'''
import java.io.*;
import java.nio.file.*;

/*
 * A plain block comment
 */

public enum Day {
    MON, TUE, WED, THU, FRI, SAT, SUN;
}

class A {
    // before inner
    class B {
        class C {
            void methodC1() {}
            void methodC2() {
                Runnable r = () -> {};
            }
        }
    }

    @Override
    public String toString() {
        return "A";
    }
}

interface I {
    void interfaceMethod();
}
'''

def dump(elements, indent=0):
    for el in elements:
        pad = "    " * indent
        print(f"{pad}{el.identifier:30}  line={el.line_start:>3}  header={el.header!r}")
        if el.description:
            first = el.description.splitlines()[0]
            print(f"{pad}    doc: {first!r}")
        dump(el.elements, indent + 1)

if __name__ == "__main__":
    print("===== SCRIPT 1 =====\n")
    dump(parse_java_elements(script_1))
    print("\n===== SCRIPT 2 =====\n")
    dump(parse_java_elements(script_2))
