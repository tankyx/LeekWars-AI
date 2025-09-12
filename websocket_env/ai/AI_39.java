import leekscript.runner.*;
import leekscript.runner.values.*;
import leekscript.runner.classes.*;
import leekscript.common.*;

public class AI_39 extends AI {
public AI_39() throws LeekRunException {
super(1, 4);
}
public void staticInit() throws LeekRunException {
}
public Object runIA(Session session) throws LeekRunException {
resetCounter();
return ops(System_debug_x("No enemy found"), 100);
}
protected String getAIString() { return "<snippet 39>";}
protected String[] getErrorFiles() { return new String[] {"<snippet 39>", };}

protected int[] getErrorFilesID() { return new int[] {39, };}

private Object System_debug_x(Object a0) throws LeekRunException {
return SystemClass.debug(this, a0);
}

}
