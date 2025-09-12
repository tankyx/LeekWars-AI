import leekscript.runner.*;
import leekscript.runner.values.*;
import leekscript.runner.classes.*;
import leekscript.common.*;

public class AI_22 extends AI {
public AI_22() throws LeekRunException {
super(1, 4);
}
public void staticInit() throws LeekRunException {
}
public Object runIA(Session session) throws LeekRunException {
resetCounter();
return ops(System_debug_x("Moved toward enemy"), 100);
}
protected String getAIString() { return "<snippet 22>";}
protected String[] getErrorFiles() { return new String[] {"<snippet 22>", };}

protected int[] getErrorFilesID() { return new int[] {22, };}

private Object System_debug_x(Object a0) throws LeekRunException {
return SystemClass.debug(this, a0);
}

}
