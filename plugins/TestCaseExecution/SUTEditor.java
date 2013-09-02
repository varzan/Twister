/*
File: SUTEditor.java ; This file is part of Twister.
Version: 2.001

Copyright (C) 2012-2013 , Luxoft

Authors: Andrei Costachi <acostachi@luxoft.com>
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTree;
import java.awt.BorderLayout;
import java.util.List;
import java.util.ArrayList;
import java.awt.datatransfer.UnsupportedFlavorException;
import javax.swing.tree.TreeNode;
import java.awt.datatransfer.Transferable;
import javax.swing.JComponent;
import java.awt.datatransfer.DataFlavor;
import javax.swing.TransferHandler;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.TreePath;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.DropMode;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JTextField;
import java.awt.Dimension;
import javax.swing.event.TreeSelectionListener;
import javax.swing.event.TreeSelectionEvent;
import java.awt.event.ActionListener;
import java.awt.event.ActionEvent;
import javax.swing.JOptionPane;
import com.twister.CustomDialog;
import javax.swing.tree.TreeSelectionModel;
import java.util.HashMap;
import org.apache.xmlrpc.client.XmlRpcClient;
import org.apache.xmlrpc.client.XmlRpcClientConfigImpl;
import java.net.URL;
import java.util.Set;
import java.util.Iterator;
import javax.swing.JList;
import javax.swing.DefaultComboBoxModel;
import java.util.Arrays;
import java.util.Enumeration;

public class SUTEditor extends JPanel{
    private JTextField tsutname;
    private JButton remsut;
    private JTree tree;
    private XmlRpcClient client;
    private Node parent;
    public DefaultMutableTreeNode root;
    private JButton renamesut;
    
    public SUTEditor(){
        initializeRPC();
        tree = new JTree();
        tree.getSelectionModel().setSelectionMode(TreeSelectionModel.SINGLE_TREE_SELECTION);
        root = new DefaultMutableTreeNode("root");
//         parent = getTB("/",null);
        DefaultTreeModel treemodel = new DefaultTreeModel(root,true);
        tree.setModel(treemodel);
        tree.setDragEnabled(true);
        tree.setRootVisible(false);
        tree.setDropMode(DropMode.ON_OR_INSERT);
        tree.setTransferHandler(new ImportTreeTransferHandler());
        tree.setDragEnabled(true);
        tree.setCellRenderer(new CustomIconRenderer());
        setLayout(new BorderLayout());
        JScrollPane sp = new JScrollPane(tree);
        add(sp,BorderLayout.CENTER);
        JPanel sutopt = new JPanel();
        
//         JButton setep = new JButton("Set EP's");
//         setep.addActionListener(new ActionListener(){
//             public void actionPerformed(ActionEvent ev){
//                 setEps();
//             }});
//         sutopt.add(setep);
        
        renamesut = new JButton("Modify SUT");
        renamesut.setEnabled(false);
        renamesut.addActionListener(new ActionListener(){
            public void actionPerformed(ActionEvent ev){
                TreePath tp = tree.getSelectionPath();
                DefaultMutableTreeNode treenode = (DefaultMutableTreeNode)tp.getLastPathComponent();
                if(treenode.getLevel()!=1)return;
                
                
                
                JPanel p = new JPanel();
                p.setLayout(null);
                p.setPreferredSize(new Dimension(250,200));
                JLabel sut = new JLabel("SUT name: ");
                sut.setBounds(5,5,80,25);
                JTextField tsut = new JTextField(treenode.toString());
                tsut.setBounds(90,5,155,25);
                JLabel ep = new JLabel("Run on EP's: ");
                ep.setBounds(5,35,80,25);
                JList tep = new JList();
                JScrollPane scep = new JScrollPane(tep);
                scep.setBounds(90,35,155,150);
                p.add(sut);
                p.add(tsut);
                p.add(ep);
                p.add(scep);
                SUT s = (SUT)treenode.getUserObject();
                populateEPs(tep,s.getEPs());
                
                
//                 s.getEPs();
//                 
//                 String [] strings = s.getEPs().split(";");
//                 int [] sel = new int[strings.length];
//                 for(int i=0;i<strings.length;i++){
//                     sel[i]=array.indexOf(strings[i]);
//                 }
//                 tep.setSelectedIndices(sel);
//                 
                
                
                
                int resp = (Integer)CustomDialog.showDialog(p,JOptionPane.PLAIN_MESSAGE, 
                            JOptionPane.OK_CANCEL_OPTION, SUTEditor.this, "Modify SUT",null);
                            
                if(resp == JOptionPane.OK_OPTION&&!tsut.getText().equals("")){
                    if(checkExistingName(root, tsut.getText(),treenode)){
                        CustomDialog.showInfo(JOptionPane.WARNING_MESSAGE,SUTEditor.this,"Warning", 
                                        "There is a SUT with the same name, please use different name.");
                         return;
                    }
                    try{
                        String query = client.execute("renameSut", new Object[]{"/"+treenode.toString(),
                                                                                        tsut.getText()}).toString();
                        if(query.equals("true")){
                            StringBuilder sb = new StringBuilder();
                            for(int i=0;i<tep.getSelectedValuesList().size();i++){
                                sb.append(tep.getSelectedValuesList().get(i).toString());
                                sb.append(";");
                            }
                            String seleps = "{'epnames':'"+sb.toString()+"'}";
                            query = client.execute("setSut", new Object[]{"/"+tsut.getText(),"/",seleps}).toString();
                            if(query.indexOf("ERROR")==-1){
                                s.setName(tsut.getText());
                                s.setEPs(sb.toString());
                                ((DefaultTreeModel)tree.getModel()).nodeChanged(treenode);
                                ((DefaultTreeModel)tree.getModel()).nodeChanged(s.getEPNode());
                            } else {
                                System.out.println(query);
                                CustomDialog.showInfo(JOptionPane.ERROR_MESSAGE,SUTEditor.this,"Error", query);
                            }
                        }else{
                            System.out.println(query);
                            CustomDialog.showInfo(JOptionPane.ERROR_MESSAGE,SUTEditor.this,"Error", query);
                        }
                    } catch (Exception e){
                        e.printStackTrace();
                    }
                    
                    
                }
                
//                 String user = CustomDialog.showInputDialog(JOptionPane.QUESTION_MESSAGE,
//                                                     JOptionPane.OK_CANCEL_OPTION, SUTEditor.this,
//                                                     "SUT Name", "Please enter SUT name");
//                 if(user!=null&&!user.equals("NULL")){
//                     try{String resp = client.execute("renameSut", new Object[]{"/"+treenode.toString(),user}).toString();
//                         if(resp.indexOf("ERROR")==-1){
//                             treenode.setUserObject(user);
//                             ((DefaultTreeModel)tree.getModel()).nodeChanged(treenode);
//                         } else {
//                             CustomDialog.showInfo(JOptionPane.WARNING_MESSAGE,SUTEditor.this,"Warning", resp);
//                         }
//                     } catch(Exception e){
//                         e.printStackTrace();
//                     }
//                 }
                
                
                
                
            }
        });
        sutopt.add(renamesut);
        JButton addsut = new JButton("Add SUT");
        addsut.addActionListener(new ActionListener(){
            public void actionPerformed(ActionEvent ev){
                JPanel p = new JPanel();
                p.setLayout(null);
                p.setPreferredSize(new Dimension(250,200));
                JLabel sut = new JLabel("SUT name: ");
                sut.setBounds(5,5,80,25);
                JTextField tsut = new JTextField();
                tsut.setBounds(90,5,155,25);
                JLabel ep = new JLabel("Run on EP's: ");
                ep.setBounds(5,35,80,25);
                JList tep = new JList();
                JScrollPane scep = new JScrollPane(tep);
                scep.setBounds(90,35,155,150);
                p.add(sut);
                p.add(tsut);
                p.add(ep);
                p.add(scep);
                populateEPs(tep,null);
                
                int resp = (Integer)CustomDialog.showDialog(p,JOptionPane.PLAIN_MESSAGE, 
                            JOptionPane.OK_CANCEL_OPTION, SUTEditor.this, "New SUT",null);
                            
                if(resp == JOptionPane.OK_OPTION&&!tsut.getText().equals("")){
                    if(checkExistingName(root, tsut.getText(),null)){
                        CustomDialog.showInfo(JOptionPane.WARNING_MESSAGE,SUTEditor.this,"Warning", 
                                        "There is a SUT with the same name, please use different name.");
                         return;
                    }
                    try{
                        StringBuilder sb = new StringBuilder();
                        for(int i=0;i<tep.getSelectedValuesList().size();i++){
                            sb.append(tep.getSelectedValuesList().get(i).toString());
                            sb.append(";");
                        }
                        String query = "{'epnames':'"+sb.toString()+"'}";
                        
                        
                        String user = tsut.getText();
                        String respons = client.execute("setSut", new Object[]{user,"/",query}).toString();
                        if(respons.indexOf("ERROR")==-1){
                            
                            DefaultTreeModel model = (DefaultTreeModel)tree.getModel();
//                             DefaultMutableTreeNode root = (DefaultMutableTreeNode)model.getRoot();
                            

                            SUT s = new SUT(user,sb.toString());
                            DefaultMutableTreeNode eps = new DefaultMutableTreeNode("EP: "+sb.toString(),false);
                            s.setEPNode(eps);
                            
                            DefaultMutableTreeNode element = new DefaultMutableTreeNode(s);
                            element.add(eps);
                            
                            model.insertNodeInto(element, root, root.getChildCount());
                        } else {
                            CustomDialog.showInfo(JOptionPane.WARNING_MESSAGE,SUTEditor.this,"Warning", respons);
                        }
                    }
                    catch(Exception e){
                        e.printStackTrace();
                    }   
                }
            }
        });
        
        remsut = new JButton("Remove");
        remsut.setEnabled(false);
        remsut.addActionListener(new ActionListener(){
            public void actionPerformed(ActionEvent ev){
                TreePath tp = tree.getSelectionPath();
                if(tp==null||tp.getPathCount()==0)return;
                DefaultMutableTreeNode treenode = (DefaultMutableTreeNode)tp.getLastPathComponent();
                if(treenode.getLevel()>2)return;
                
                try{
                    String torem = "/"+treenode.toString();
                    if(treenode.getLevel()!=1){
                        Node node = (Node)treenode.getUserObject();
                        torem = "/"+treenode.getParent().toString()+"/"+node.getID();
                        
//                         torem = node.getID();
                    }
                    String s = client.execute("deleteSut", new Object[]{torem}).toString();
                    if(s.indexOf("ERROR")==-1){
                        if(treenode.getLevel()!=1){
                            Node node = (Node)treenode.getUserObject();
                            Node parent = node.getParent();
                            if(parent!=null){
                                parent.removeChild(node.getID());
                            }
                        }
                        ((DefaultTreeModel)tree.getModel()).removeNodeFromParent(treenode);
                        selectedSUT(null);
                    } else {
                        CustomDialog.showInfo(JOptionPane.WARNING_MESSAGE,SUTEditor.this,"Warning", s);
                    }
                } catch (Exception e){
                    e.printStackTrace();
                }
            }
        });
        sutopt.add(renamesut);
        sutopt.add(addsut);
        sutopt.add(remsut);
        add(sutopt,BorderLayout.SOUTH);        
        tree.addTreeSelectionListener(new TreeSelectionListener(){
            public void valueChanged(TreeSelectionEvent ev){                
                TreePath newPath = ev.getNewLeadSelectionPath();                 
                DefaultMutableTreeNode newNode = null;  
                if(newPath != null){
                    newNode = (DefaultMutableTreeNode)newPath.getLastPathComponent();
                    selectedSUT(newNode);
                } else {
                    selectedSUT(null);
                }
            }
        });
        getSUT();
    }
    
//     private void setEps(){
//         JList tep = new JList();
//         JScrollPane epscroll = new JScrollPane(tep);
//         epscroll.setPreferredSize(new Dimension(150,200));
//         JPanel p = new JPanel();
//         p.add(epscroll);
//         populateEPs(tep);
//         int resp = (Integer)CustomDialog.showDialog(p,JOptionPane.PLAIN_MESSAGE, 
//                             JOptionPane.OK_CANCEL_OPTION, SUTEditor.this, "Run on EP: ",null);
//         if(resp == JOptionPane.OK_OPTION){
//             Object [] selections = tep.getSelectedValues();
//         }
//     }

    public boolean checkExistingName(DefaultMutableTreeNode parent, String name, DefaultMutableTreeNode current){
        Enumeration e = parent.children();
        while(e.hasMoreElements()){
            DefaultMutableTreeNode child = (DefaultMutableTreeNode)e.nextElement();
            if(child!=current&&name.equals(child.toString())){
//                 if(current!=null&&)
                return true;
            }
        }
        
//         for(String s:parent.getChildren().keySet()){
//             if(name.equals(parent.getChildren().get(s).getName())){
//                 return true;
//             }
//         }
        return false;
    }
    
    public void populateEPs(JList tep, String eps){
        try{
            StringBuilder b = new StringBuilder();
            String st;
            for(String s:RunnerRepository.getRemoteFileContent(RunnerRepository.REMOTEEPIDDIR).split("\n")){
                if(s.indexOf("[")!=-1){
                    st = s.substring(s.indexOf("[")+1, s.indexOf("]"));
                    if(st.toUpperCase().indexOf("PLUGIN")==-1){
                        b.append(s.substring(s.indexOf("[")+1, s.indexOf("]"))+";");
                    }
                }
            }
            String [] vecresult = b.toString().split(";");
            tep.setModel(new DefaultComboBoxModel(vecresult));
            ArrayList<String> array = new ArrayList<String>(Arrays.asList(vecresult));
            
            if(eps!=null){
                String [] strings = eps.split(";");
                int [] sel = new int[strings.length];
                for(int i=0;i<strings.length;i++){
                    sel[i]=array.indexOf(strings[i]);
                }
                tep.setSelectedIndices(sel);
            }
            
        } catch (Exception e){e.printStackTrace();}
    }
    
    private void selectedSUT(DefaultMutableTreeNode newNode){
        
        if(newNode!=null){
            if(newNode.getUserObject()  instanceof SUT){
                renamesut.setEnabled(true);
            } else {
                renamesut.setEnabled(false);
            }
            
            if(newNode.getLevel()<3&&!newNode.isLeaf()){
                remsut.setEnabled(true);
            } else{
                remsut.setEnabled(false); 
            }
//             if(newNode.getLevel()>2){
//                 remsut.setEnabled(false);                
//             } else {
//                 remsut.setEnabled(true);
//             }
            
        } else{
            remsut.setEnabled(false);
            renamesut.setEnabled(false);
        }
    }
    
    public void getSUT(){
        try{HashMap hash= (HashMap)client.execute("getSut", new Object[]{"/"});
            Object[] children = (Object[])hash.get("children");
            DefaultMutableTreeNode child,epsnode;
            DefaultTreeModel model = (DefaultTreeModel)tree.getModel();
            root.removeAllChildren();
            model.reload();
            String name,path,eps;
            Object[] subchildren;
            for(Object o:children){
                hash= (HashMap)client.execute("getSut", new Object[]{o.toString()});
                path = hash.get("path").toString();
                name = path.split("/")[path.split("/").length-1];
                try{eps = ((HashMap)hash.get("meta")).get("epnames").toString();}
                catch(Exception e){eps = "";}
                SUT s = new SUT(name,eps);
                epsnode = new DefaultMutableTreeNode("EP: "+eps,false);
                s.setEPNode(epsnode);
                child = new DefaultMutableTreeNode(s);
                child.add(epsnode);                
                subchildren = (Object[])hash.get("children");
                for(Object ob:subchildren){
                    String childid = ob.toString();
                    HashMap subhash= (HashMap)client.execute("getSut", new Object[]{childid});
                    String subpath = subhash.get("path").toString();
                    String subname = subpath.split("/")[subpath.split("/").length-1];
                    buildChildren(new Object[]{subname},child,null);
                }
                model.insertNodeInto(child, root, root.getChildCount());
            }
        } catch (Exception e){
            e.printStackTrace();
        }
    }
    
    private void buildChildren(Object [] children, DefaultMutableTreeNode treenode, Node parent){
        String childid, subchildid;
        for(Object o:children){
            childid = o.toString();
            try{                
                Node child = getTB(childid,parent);
                DefaultMutableTreeNode treechild = new DefaultMutableTreeNode(child);
                ((DefaultTreeModel)tree.getModel()).insertNodeInto(treechild, treenode,treenode.getChildCount());
                DefaultMutableTreeNode temp = new DefaultMutableTreeNode("ID: "+child.getID(),false);
                ((DefaultTreeModel)tree.getModel()).insertNodeInto(temp, treechild,treechild.getChildCount());
                DefaultMutableTreeNode temp2 = new DefaultMutableTreeNode(child.getPath(),false);
                ((DefaultTreeModel)tree.getModel()).insertNodeInto(temp2, treechild,treechild.getChildCount());
                Object []  subchildren = child.getChildren().keySet().toArray();
                buildChildren(subchildren,treechild,child);
            }catch(Exception e){
                e.printStackTrace();
            }
        }
    }
    
    /*
     * create a node based om an id
     * the node is created from the data 
     * received from server
     */
    public Node getTB(String id,Node parent){
        try{
            HashMap hash= (HashMap)client.execute("getResource", new Object[]{id});
            String path = hash.get("path").toString();
            String name = path.split("/")[path.split("/").length-1];
            byte type = 1;
            if(path.indexOf("/")==-1){
                type = 0;
            }
            Node node = new Node(id,path,name,parent,null,type);
            Object[] children = (Object[])hash.get("children");
            for(Object o:children){
                node.addChild(o.toString(), null);
            }
            HashMap meta = (HashMap)hash.get("meta");
            if(meta!=null&&meta.size()!=0){
                Set keys = meta.keySet();
                Iterator iter = keys.iterator();
                while(iter.hasNext()){
                    String n = iter.next().toString();
                    if(n.equals("epnames")){
                        node.setEPs(meta.get(n).toString());
                        continue;
                    }
                    node.addProperty(n, meta.get(n).toString());
                }
            }
            return node;
        }catch(Exception e){
            System.out.println("requested id: "+id);
            try{System.out.println("server respons: "+client.execute("getResource", new Object[]{id}));}
            catch(Exception ex){ex.printStackTrace();}
            e.printStackTrace();
            return null;
        }
    }
//         try{
//             
//             for(Object ob:children){
//                 String childid = ob.toString();
//                 
// //                 Node child = getTB(childid,node);
// //                 node.addChild(childid, child);
//                 DefaultMutableTreeNode treechild = new DefaultMutableTreeNode(child);
//                 ((DefaultTreeModel)tree.getModel()).insertNodeInto(treechild, treenode,treenode.getChildCount());
//                 DefaultMutableTreeNode temp = new DefaultMutableTreeNode("ID: "+child.getID());
//                 ((DefaultTreeModel)tree.getModel()).insertNodeInto(temp, treechild,treechild.getChildCount());
//                 DefaultMutableTreeNode temp2 = new DefaultMutableTreeNode(child.getPath());
//                 ((DefaultTreeModel)tree.getModel()).insertNodeInto(temp2, treechild,treechild.getChildCount());
//                 
//                 HashMap hash= (HashMap)client.execute("getSut", new Object[]{child});
//                 Object[] children = (Object[])hash.get("children");
//                 buildChildren(children,treechild);
//                 
//                 
//                 
//             }
//         } catch(Exception e){
//             e.printStackTrace();
//         }
//     }
    
    
    /*
     * initialize RPC connection
     * based on host an port of 
     * resource allocator specified in config
     */
    public void initializeRPC(){
        try{XmlRpcClientConfigImpl configuration = new XmlRpcClientConfigImpl();
            configuration.setServerURL(new URL("http://"+RunnerRepository.host+
                                        ":"+RunnerRepository.getCentralEnginePort()+"/ra/"));
            configuration.setEnabledForExtensions(true);
            configuration.setBasicPassword(RunnerRepository.password);
            configuration.setBasicUserName(RunnerRepository.user);
            client = new XmlRpcClient();
            client.setConfig(configuration);
            System.out.println("XMLRPC Client for testbed initialized: "+client);}
        catch(Exception e){System.out.println("Could not conect to "+
                            RunnerRepository.host+" :"+RunnerRepository.getCentralEnginePort()+"/ra/"+
                            "for RPC client initialization");}
    }
    
    class ImportTreeTransferHandler extends TransferHandler {  
    
    
        DataFlavor nodesFlavor;  
        DataFlavor[] flavors = new DataFlavor[1];
       
        public ImportTreeTransferHandler() {  
            try {  
                String mimeType = DataFlavor.javaJVMLocalObjectMimeType +  
                                  ";class=\"" +  
                                  Node.class.getName() +  
                                  "\"";  
                nodesFlavor = new DataFlavor(mimeType);  
                flavors[0] = nodesFlavor;  
            } catch(ClassNotFoundException e) {  
                System.out.println("ClassNotFound: " + e.getMessage());  
            }  
        }  
       
        public boolean canImport(TransferHandler.TransferSupport support) {  
            if(!support.isDrop()) {  
                return false;  
            }  
            support.setShowDropLocation(true);  
            if(!support.isDataFlavorSupported(nodesFlavor)) {  
                return false;  
            }  
            JTree.DropLocation dl = (JTree.DropLocation)support.getDropLocation(); 
            TreePath dest = dl.getPath();  
            DefaultMutableTreeNode target = (DefaultMutableTreeNode)dest.getLastPathComponent(); 
            if(target.getLevel()!=1){
                return false;
            }
            Node[] nodes = null; 
            //check if node is allready inserted
            try{Transferable t = support.getTransferable();  
                nodes = (Node[])t.getTransferData(nodesFlavor);
                Enumeration e;
                Node node=null;
                for(Node n:nodes){
                    if(target.getLevel()==1){
                        e = target.children();
                        while(e.hasMoreElements()){
                            Object ob= ((DefaultMutableTreeNode)e.nextElement()).getUserObject();
                            if(!(ob instanceof Node))continue;
                            node = (Node)ob;
                            if(n.getID().equals(node.getID())){
                                return false;
                            }
                        }
                    }
                }
            } catch (Exception e){
                e.printStackTrace();
            }
            return true;  
        }
         
        private DefaultMutableTreeNode copy(TreeNode node) {  
            return new DefaultMutableTreeNode(node);  
        }  
       
        public int getSourceActions(JComponent c) {  
            return COPY;  
        }  
       
        public boolean importData(TransferHandler.TransferSupport support) {  
            if(!canImport(support)) {  
                return false;  
            }  
            Node[] nodes = null;  
            try {  
                Transferable t = support.getTransferable();  
                nodes = (Node[])t.getTransferData(nodesFlavor);  
            } catch(UnsupportedFlavorException ufe) {  
                System.out.println("UnsupportedFlavor: " + ufe.getMessage());  
            } catch(java.io.IOException ioe) {  
                System.out.println("I/O error: " + ioe.getMessage());  
            }
            JTree.DropLocation dl = (JTree.DropLocation)support.getDropLocation();  
            TreePath dest = dl.getPath();  
            DefaultMutableTreeNode parent = (DefaultMutableTreeNode)dest.getLastPathComponent();  
            JTree tree = (JTree)support.getComponent();  
            DefaultTreeModel model = (DefaultTreeModel)tree.getModel();  
            int index = parent.getChildCount();  
//             }
            for(int i = 0; i < nodes.length; i++) { 
                try{
                    String resp = client.execute("setSut", new Object[]{nodes[i].getID(),"/"+parent.getPath()[parent.getPath().length-1],null}).toString();
                    if(resp.indexOf("ERROR")==-1){
                        DefaultMutableTreeNode element = createChildren(nodes[i]);
                        model.insertNodeInto(element, parent, index++);
                    }
                    
                } catch (Exception e){
                    e.printStackTrace();
                }
                
            } 
            return true;  
        } 
        
        private DefaultMutableTreeNode createChildren(Node node){
            DefaultMutableTreeNode parent = new DefaultMutableTreeNode(node);
            
            DefaultMutableTreeNode temp = new DefaultMutableTreeNode("ID: "+node.getID(),false);
            parent.add(temp);
            
            temp = new DefaultMutableTreeNode(node.getPath(),false);
            parent.add(temp);
            
            
            Object [] objects = node.getChildren().values().toArray();
            try{
                for(Object ob:objects){
                    Node n = (Node)ob;
                    DefaultMutableTreeNode child = createChildren(n);
                    parent.add(child);
                }
            } catch (Exception e){
                e.printStackTrace();
            }
            
            return parent;
        }
       
        public String toString() {  
            return getClass().getName();  
        }  
       
        public class NodesTransferable implements Transferable {  
            DefaultMutableTreeNode[] nodes;  
       
            public NodesTransferable(DefaultMutableTreeNode[] nodes) {  
                this.nodes = nodes;  
             }  
       
            public Object getTransferData(DataFlavor flavor)  
                                     throws UnsupportedFlavorException {  
                if(!isDataFlavorSupported(flavor))  
                    throw new UnsupportedFlavorException(flavor);  
                return nodes;  
            }  
       
            public DataFlavor[] getTransferDataFlavors() {  
                return flavors;  
            }  
       
            public boolean isDataFlavorSupported(DataFlavor flavor) {  
                return nodesFlavor.equals(flavor);  
            }  
        }  
    }
}