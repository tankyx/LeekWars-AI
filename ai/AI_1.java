import leekscript.runner.*;
import leekscript.runner.values.*;
import leekscript.runner.classes.*;
import leekscript.common.*;

public class AI_1 extends AI {
public AI_1() throws LeekRunException {
super(1, 4);
}
public void staticInit() throws LeekRunException {
}
public Object runIA(Session session) throws LeekRunException {
resetCounter();
return ops(System_debug_x("Hello world"), 100);
}
protected String getAIString() { return "<snippet 1>";}
protected String[] getErrorFiles() { return new String[] {"<snippet 1>", };}

protected int[] getErrorFilesID() { return new int[] {1, };}

private Object System_debug_x(Object a0) throws LeekRunException {
return SystemClass.debug(this, a0);
}

}
