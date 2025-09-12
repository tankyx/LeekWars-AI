import leekscript.runner.*;
import leekscript.runner.values.*;
import leekscript.runner.classes.*;
import leekscript.common.*;

public class AI_42 extends AI {
public AI_42() throws LeekRunException {
super(1, 4);
}
public void staticInit() throws LeekRunException {
}
public Object runIA(Session session) throws LeekRunException {
resetCounter();
return ops(System_debug_x("V8 Minimal Test Complete"), 100);
}
protected String getAIString() { return "<snippet 42>";}
protected String[] getErrorFiles() { return new String[] {"<snippet 42>", };}

protected int[] getErrorFilesID() { return new int[] {42, };}

private Object System_debug_x(Object a0) throws LeekRunException {
return SystemClass.debug(this, a0);
}

}
